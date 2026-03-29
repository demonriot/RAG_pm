# app/reasoning/prereq_checker.py

from __future__ import annotations

from typing import Any, Dict, List

from app.reasoning.prereq_extractor import extract_prereq_text
from app.reasoning.prereq_parser import parse_prerequisite_text
from app.reasoning.prereq_evaluator import normalize_completed_courses, evaluate_prereq


BLOCKING_FLAG_PREFIXES = [
    "unsupported:",
]

BLOCKING_EXACT_FLAGS = {
    "parse_failed",
    "no_parseable_course_logic",
    "empty_prerequisite_text",
    "ambiguous_and_or_without_parentheses",
}


def decide_eligibility(eval_result: Dict[str, Any], parser_flags: List[str]) -> str:
    status = eval_result.get("status")

    has_missing_courses = bool(eval_result.get("missing_courses"))
    has_min_grade = any("minimum_grade" in f.lower() for f in parser_flags)
    has_concurrent = any("concurrent" in f.lower() for f in parser_flags)
    has_placement = any("placement_test" in f.lower() for f in parser_flags)

    has_other_blocking_flags = any(
        f in {
            "parse_failed",
            "no_parseable_course_logic",
            "empty_prerequisite_text",
            "ambiguous_and_or_without_parentheses",
        }
        or f.startswith("unsupported:INSTRUCTOR")
        or f.startswith("unsupported:APPROVAL")
        or f.startswith("unsupported:CLASS STANDING")
        or f.startswith("unsupported:MAJOR")
        or f.startswith("unsupported:MINOR")
        or f.startswith("unsupported:GPA")
        or f.startswith("unsupported:PERMISSION")
        for f in parser_flags
    )

    # If parseable course requirements are clearly not met, that is enough for not eligible.
    if status == "not_satisfied" or has_missing_courses:
        return "not_eligible"

    # If parseable course requirements are met, but grade/concurrent/placement conditions remain unknown
    if status == "satisfied":
        if has_min_grade or has_concurrent or has_placement or has_other_blocking_flags:
            return "need_more_info"
        return "eligible"

    return "need_more_info"


def build_reasoning_and_next_steps(
    decision: str,
    eval_result: Dict[str, Any],
    parser_flags: List[str],
) -> tuple[str, List[str]]:
    matched = eval_result.get("matched_courses", [])
    missing = eval_result.get("missing_courses", [])

    has_min_grade = any("minimum_grade" in f.lower() for f in parser_flags)
    has_concurrent = any("concurrent" in f.lower() for f in parser_flags)
    has_placement = any("placement_test" in f.lower() for f in parser_flags)

    if decision == "eligible":
        if matched:
            reasoning = (
                f"Based on the retrieved catalog evidence, you satisfy the listed prerequisite course requirements "
                f"because you have completed: {', '.join(sorted(set(matched)))}."
            )
        else:
            reasoning = "Based on the retrieved catalog evidence, you satisfy the listed prerequisites."
        return reasoning, []

    if decision == "not_eligible":
        reasoning = "Based on the retrieved catalog evidence, you do not currently satisfy the listed prerequisite course requirements."
        next_steps = []
        if missing:
            next_steps.append(
                f"Complete the missing prerequisite course(s): {', '.join(sorted(set(missing)))}."
            )
        else:
            next_steps.append("Review the full prerequisite wording in the course catalog.")
        return reasoning, next_steps

    reasons = []
    if has_min_grade:
        reasons.append("minimum grade requirements")
    if has_concurrent:
        reasons.append("concurrent enrollment conditions")
    if has_placement:
        reasons.append("placement test conditions")

    if reasons:
        reasoning = (
            "The retrieved catalog prerequisite text includes "
            + ", ".join(reasons)
            + ", so eligibility cannot be determined with full confidence from completed course codes alone."
        )
    else:
        reasoning = (
            "The retrieved catalog prerequisite text could not be evaluated with full confidence "
            "using the deterministic prerequisite checker."
        )

    next_steps = []
    if has_min_grade:
        next_steps.append("Verify that the required prerequisite course was completed with the minimum required grade.")
    if has_concurrent:
        next_steps.append("Check whether concurrent enrollment is allowed and whether it applies to your case.")
    if has_placement:
        next_steps.append("Check whether placement test scores can satisfy the prerequisite.")
    if missing:
        next_steps.append(
            f"You may also need to complete: {', '.join(sorted(set(missing)))}."
        )
    if not next_steps:
        next_steps.append("Review the exact catalog wording for special conditions.")

    return reasoning, next_steps


def build_citations(chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {
            "citation_label": chunk.get("citation_label") or chunk.get("section") or chunk.get("section_path"),
            "source_url": chunk.get("source_url"),
            "section_path": chunk.get("section") or chunk.get("section_path"),
            "catalog_year": chunk.get("catalog_year"),
            "storage_path": chunk.get("storage_path"),
        }
    ]


def check_prereq_from_chunk(
    *,
    target_course: str,
    completed_courses: List[str],
    chunk: Dict[str, Any],
) -> Dict[str, Any]:
    content = chunk.get("text") or chunk.get("content") or ""

    prereq_text = extract_prereq_text(content)

    content_upper = content.upper()

    has_prereq_label = "PREREQUISITE:" in content_upper or "PREREQUISITES:" in content_upper

    if not prereq_text:
        if has_prereq_label:
            # We expected to extract something but failed
            return {
                "target_course": target_course,
                "decision": "need_more_info",
                "evidence": None,
                "reasoning": "A prerequisite label was found in the retrieved course content, but the prerequisite text could not be extracted reliably.",
                "next_steps": [
                    "Review the full course page.",
                    "Verify whether the retrieved chunk contains the complete prerequisite section.",
                ],
                "citations": build_citations(chunk),
                "debug": {
                    "parsed_prerequisites": None,
                    "parser_flags": ["prerequisite_label_present_but_extraction_failed"],
                    "matched_courses": [],
                    "missing_courses": [],
                },
            }
        else:
            # No prerequisite label at all -> assume no prerequisites listed
            return {
                "target_course": target_course,
                "decision": "eligible",
                "evidence": None,
                "reasoning": "No prerequisites are listed for this course in the retrieved catalog content.",
                "next_steps": [],
                "citations": build_citations(chunk),
                "debug": {
                    "parsed_prerequisites": None,
                    "parser_flags": ["no_prerequisite_listed"],
                    "matched_courses": [],
                    "missing_courses": [],
                },
            }

    parse_result = parse_prerequisite_text(prereq_text)
    node = parse_result["node"]
    parser_flags = parse_result["flags"]

    completed_normalized = normalize_completed_courses(completed_courses)
    eval_result = evaluate_prereq(node, completed_normalized)

    decision = decide_eligibility(eval_result, parser_flags)
    reasoning, next_steps = build_reasoning_and_next_steps(decision, eval_result, parser_flags)

    return {
        "target_course": target_course,
        "decision": decision,
        "evidence": prereq_text,
        "reasoning": reasoning,
        "next_steps": next_steps,
        "citations": build_citations(chunk),
        "debug": {
            "parsed_prerequisites": node,
            "parser_flags": parser_flags,
            "matched_courses": eval_result.get("matched_courses", []),
            "missing_courses": eval_result.get("missing_courses", []),
            "evaluation_status": eval_result.get("status"),
        },
    }