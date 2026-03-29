# app/planning/eligibility_planner.py

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.reasoning.prereq_checker import check_prereq_from_chunk
from app.retrieval.course_lookup import get_course_chunk_by_code


def normalize_course_code(course_code: str) -> str:
    if not course_code:
        return ""

    raw = course_code.upper().strip()
    raw = " ".join(raw.split())

    m = re.fullmatch(r"([A-Z]{2,4})\s?(\d{3}[A-Z]?)", raw)
    if m:
        return f"{m.group(1)} {m.group(2)}"

    return raw


def course_sort_key(course_code: str):
    code = normalize_course_code(course_code)
    m = re.fullmatch(r"([A-Z]{2,4})\s(\d{3}[A-Z]?)", code)
    if not m:
        return (code, 9999, "")
    subject = m.group(1)
    number_part = m.group(2)

    num_match = re.match(r"(\d{3})([A-Z]?)", number_part)
    if not num_match:
        return (subject, 9999, number_part)

    return (subject, int(num_match.group(1)), num_match.group(2))


def build_missing_course_result(course_code: str) -> Dict[str, Any]:
    normalized = normalize_course_code(course_code)
    return {
        "course_code": normalized,
        "title": None,
        "decision": "need_more_info",
        "reasoning": f"No course chunk could be retrieved for {normalized}.",
        "evidence": None,
        "citations": [],
        "next_steps": [
            "Verify that the course exists in the ingested catalog.",
            "Check whether this course code was ingested correctly.",
        ],
    }


def evaluate_course_eligibility(
    *,
    target_course: str,
    completed_courses: List[str],
) -> Dict[str, Any]:
    normalized_target = normalize_course_code(target_course)
    chunk = get_course_chunk_by_code(normalized_target)

    if not chunk:
        return build_missing_course_result(normalized_target)

    result = check_prereq_from_chunk(
        target_course=normalized_target,
        completed_courses=completed_courses,
        chunk=chunk,
    )

    title = chunk.get("section") or chunk.get("section_path") or chunk.get("title")

    return {
        "course_code": normalized_target,
        "title": title,
        "decision": result["decision"],
        "reasoning": result["reasoning"],
        "evidence": result["evidence"],
        "citations": result["citations"],
        "next_steps": result["next_steps"],
        "debug": result.get("debug"),
    }


def plan_course_options(
    *,
    completed_courses: List[str],
    candidate_courses: List[str],
) -> Dict[str, Any]:
    normalized_completed = [normalize_course_code(c) for c in completed_courses]
    normalized_candidates = [normalize_course_code(c) for c in candidate_courses]

    eligible_now: List[Dict[str, Any]] = []
    not_eligible: List[Dict[str, Any]] = []
    need_more_info: List[Dict[str, Any]] = []

    seen = set()
    completed_set = set(normalized_completed)

    for course_code in normalized_candidates:
        if not course_code or course_code in seen or course_code in completed_set:
            continue
        seen.add(course_code)

        result = evaluate_course_eligibility(
            target_course=course_code,
            completed_courses=normalized_completed,
        )

        decision = result["decision"]

        if decision == "eligible":
            eligible_now.append(result)
        elif decision == "not_eligible":
            not_eligible.append(result)
        else:
            need_more_info.append(result)

    eligible_now.sort(key=lambda x: course_sort_key(x["course_code"]))
    not_eligible.sort(key=lambda x: course_sort_key(x["course_code"]))
    need_more_info.sort(key=lambda x: course_sort_key(x["course_code"]))

    return {
        "completed_courses": sorted(set(normalized_completed), key=course_sort_key),
        "eligible_now": eligible_now,
        "not_eligible": not_eligible,
        "need_more_info": need_more_info,
        "summary": {
            "eligible_count": len(eligible_now),
            "not_eligible_count": len(not_eligible),
            "need_more_info_count": len(need_more_info),
            "total_candidates_checked": len(eligible_now) + len(not_eligible) + len(need_more_info),
        },
    }