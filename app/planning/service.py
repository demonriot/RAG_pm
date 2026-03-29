from __future__ import annotations

import time
from typing import Any, Dict

from app.core.schemas.planning import CoursePlanRequest, CoursePlanResponse
from app.planning.eligibility_planner import plan_course_options


class PlanningServiceError(Exception):
    pass


def run_course_planner(payload: CoursePlanRequest) -> CoursePlanResponse:
    try:
        start = time.time()

        raw_result: Dict[str, Any] = plan_course_options(
            completed_courses=payload.completed_courses,
            candidate_courses=payload.candidate_courses,
        )

        duration = time.time() - start
        print(f"[PLANNER] Execution time: {duration:.3f}s")

    except ValueError as e:
        raise PlanningServiceError(str(e)) from e
    except Exception as e:
        raise PlanningServiceError("Failed to run course planner") from e

    return CoursePlanResponse.model_validate(raw_result)