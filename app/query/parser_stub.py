from __future__ import annotations

from app.core.schemas.planning import CoursePlanRequest


def parse_query_to_plan_request(query: str) -> CoursePlanRequest:
    # Temporary stub for testing end-to-end query flow.
    # Replace later with LLM-based structured extraction.
    return CoursePlanRequest(
        completed_courses=["CS 161", "CS 162", "MTH 251"],
        candidate_courses=["CS 261"],
    )