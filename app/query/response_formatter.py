from __future__ import annotations

from typing import List, Optional

from app.core.schemas.planning import Citation, CoursePlanResponse, PlannerCourseResult
from app.core.schemas.query import FinalQueryOutput, QueryParseResult


def _flatten_results(planner_result: CoursePlanResponse) -> List[PlannerCourseResult]:
    return (
        planner_result.eligible_now
        + planner_result.not_eligible
        + planner_result.need_more_info
    )


def _collect_why_lines(planner_result: CoursePlanResponse) -> List[str]:
    lines: List[str] = []

    for item in _flatten_results(planner_result):
        if item.decision == "eligible":
            lines.append(f"{item.course_code}: prerequisites appear satisfied.")
        elif item.decision == "not_eligible":
            if item.evidence:
                lines.append(f"{item.course_code}: catalog prerequisite evidence -> {item.evidence}")
            else:
                lines.append(f"{item.course_code}: prerequisites are not currently satisfied.")
        else:
            if item.evidence:
                lines.append(f"{item.course_code}: more information is needed. Relevant evidence -> {item.evidence}")
            else:
                lines.append(f"{item.course_code}: more information is needed to determine eligibility.")

    return lines


def _build_assumptions(planner_result: CoursePlanResponse) -> List[str]:
    assumptions: List[str] = []

    for item in _flatten_results(planner_result):
        debug = item.debug or {}
        parser_flags = debug.get("parser_flags", [])

        if "unsupported:minimum_grade" in parser_flags:
            assumptions.append(
                f"{item.course_code}: minimum-grade language appears in the catalog, but grade details may be incomplete."
            )

    if planner_result.eligible_now:
        assumptions.append(
            "Course availability by specific term was not verified unless explicitly present in the catalog."
        )

    # dedupe while preserving order
    seen = set()
    deduped = []
    for a in assumptions:
        if a not in seen:
            seen.add(a)
            deduped.append(a)

    return deduped


def format_query_response(
    *,
    answer_text: str,
    citations: List[Citation],
    parsed_input: QueryParseResult,
    planner_result: Optional[CoursePlanResponse],
    clarifying_questions: Optional[List[str]] = None,
    assumptions_or_not_in_catalog: Optional[List[str]] = None,
) -> FinalQueryOutput:
    clarifying_questions = clarifying_questions or []
    assumptions_or_not_in_catalog = assumptions_or_not_in_catalog or []

    why_lines: List[str] = []

    if planner_result is not None:
        why_lines = _collect_why_lines(planner_result)
        assumptions_or_not_in_catalog = assumptions_or_not_in_catalog + _build_assumptions(planner_result)

    # dedupe assumptions
    seen = set()
    deduped_assumptions = []
    for a in assumptions_or_not_in_catalog:
        if a not in seen:
            seen.add(a)
            deduped_assumptions.append(a)

    return FinalQueryOutput(
        answer_or_plan=answer_text,
        why=why_lines,
        citations=citations,
        clarifying_questions=clarifying_questions,
        assumptions_or_not_in_catalog=deduped_assumptions,
    )