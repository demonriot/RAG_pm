from __future__ import annotations

import time
from fastapi import APIRouter, HTTPException

from app.core.schemas.planning import CoursePlanRequest, CoursePlanResponse
from app.planning.service import PlanningServiceError, run_course_planner

router = APIRouter(prefix="/plan", tags=["planning"])


@router.post("/courses")
def plan_courses(payload: CoursePlanRequest) -> CoursePlanResponse:
    start_time = time.time()

    try:
        print("\n=== /plan/courses REQUEST ===")
        print(payload.model_dump())

        result = run_course_planner(payload)

        duration = time.time() - start_time

        print("=== RESPONSE SUMMARY ===")
        print(result.summary.model_dump())
        print(f"=== TOTAL TIME: {duration:.3f}s ===\n")

        return result

    except PlanningServiceError as e:
        print(f"ERROR (400): {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) from e

    except Exception as e:
        print(f"ERROR (500): {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while planning courses",
        )