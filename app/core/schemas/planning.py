from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from app.planning.eligibility_planner import normalize_course_code


class CoursePlanRequest(BaseModel):
    completed_courses: List[str] = Field(default_factory=list)
    candidate_courses: List[str] = Field(..., min_length=1)

    @field_validator("completed_courses", "candidate_courses")
    @classmethod
    def validate_and_normalize_course_codes(cls, values: List[str]) -> List[str]:
        cleaned: List[str] = []
        seen = set()

        for value in values:
            if not isinstance(value, str):
                raise ValueError("Each course code must be a string")

            normalized = normalize_course_code(value)
            if not normalized:
                raise ValueError("Course code cannot be empty")

            if normalized not in seen:
                cleaned.append(normalized)
                seen.add(normalized)

        return cleaned


class Citation(BaseModel):
    citation_label: Optional[str] = None
    source_url: Optional[str] = None
    catalog_year: Optional[str] = None
    section: Optional[str] = None


class PlannerCourseResult(BaseModel):
    course_code: str
    title: Optional[str] = None
    decision: Literal["eligible", "not_eligible", "need_more_info"]
    reasoning: str
    evidence: Optional[str] = None
    citations: List[Citation] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    debug: Optional[Dict[str, Any]] = None


class PlannerSummary(BaseModel):
    eligible_count: int
    not_eligible_count: int
    need_more_info_count: int
    total_candidates_checked: int


class CoursePlanResponse(BaseModel):
    completed_courses: List[str] = Field(default_factory=list)
    eligible_now: List[PlannerCourseResult] = Field(default_factory=list)
    not_eligible: List[PlannerCourseResult] = Field(default_factory=list)
    need_more_info: List[PlannerCourseResult] = Field(default_factory=list)
    summary: PlannerSummary


class ErrorResponse(BaseModel):
    detail: str