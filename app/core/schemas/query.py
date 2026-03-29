from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.core.schemas.planning import Citation, CoursePlanResponse


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)


class QueryParseResult(BaseModel):
    intent: Literal["eligibility_check", "recommendation"] = "eligibility_check"
    completed_courses: List[str] = Field(default_factory=list)
    candidate_courses: List[str] = Field(default_factory=list)


class FinalQueryOutput(BaseModel):
    answer_or_plan: str
    why: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    assumptions_or_not_in_catalog: List[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    query: str
    parsed_input: QueryParseResult
    planner_result: Optional[CoursePlanResponse] = None
    output: FinalQueryOutput