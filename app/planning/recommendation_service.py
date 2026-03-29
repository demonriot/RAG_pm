from __future__ import annotations

from app.core.schemas.planning import CoursePlanResponse
from app.core.schemas.query import QueryParseResult
from app.planning.eligibility_planner import plan_course_options
from app.planning.recommendation_ranker import rank_recommendations
from app.planning.recommendations import get_recommendation_candidates


def run_recommendation_planner(parsed_input: QueryParseResult) -> CoursePlanResponse:
    candidate_courses = get_recommendation_candidates(
        completed_courses=parsed_input.completed_courses,
        subject_prefix="CS",
    )

    raw_result = plan_course_options(
        completed_courses=parsed_input.completed_courses,
        candidate_courses=candidate_courses,
    )

    result = CoursePlanResponse.model_validate(raw_result)

    result.eligible_now = rank_recommendations(
        result.eligible_now,
        completed_courses=parsed_input.completed_courses,
        limit=8,
    )

    print("RANKED RECOMMENDATIONS:", [item.course_code for item in result.eligible_now])

    return result