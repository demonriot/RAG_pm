from __future__ import annotations

from app.core.schemas.planning import CoursePlanRequest, CoursePlanResponse
from app.core.schemas.query import QueryRequest, QueryResponse
from app.planning.recommendation_service import run_recommendation_planner
from app.planning.service import run_course_planner
from app.query.answer_llm import collect_citations, generate_answer
from app.query.parser_llm import parse_query
from app.query.response_formatter import format_query_response


class QueryServiceError(Exception):
    pass


def run_query(payload: QueryRequest) -> QueryResponse:
    try:
        parsed_input = parse_query(payload.query)

        print("PARSED QUERY:", parsed_input.model_dump())
        print("QUERY INTENT:", parsed_input.intent)

        # Clarifying-question path for missing required inputs
        if parsed_input.intent == "eligibility_check":
            if not parsed_input.candidate_courses:
                output = format_query_response(
                    answer_text="I need one more detail before I can check eligibility.",
                    citations=[],
                    parsed_input=parsed_input,
                    planner_result=None,
                    clarifying_questions=[
                        "Which course would you like me to evaluate eligibility for?"
                    ],
                    assumptions_or_not_in_catalog=[],
                )
                return QueryResponse(
                    query=payload.query,
                    parsed_input=parsed_input,
                    planner_result=None,
                    output=output,
                )

            if not parsed_input.completed_courses:
                output = format_query_response(
                    answer_text="I need more information before I can check eligibility.",
                    citations=[],
                    parsed_input=parsed_input,
                    planner_result=None,
                    clarifying_questions=[
                        "Which courses have you completed so far?"
                    ],
                    assumptions_or_not_in_catalog=[],
                )
                return QueryResponse(
                    query=payload.query,
                    parsed_input=parsed_input,
                    planner_result=None,
                    output=output,
                )

            planner_input = CoursePlanRequest(
                completed_courses=parsed_input.completed_courses,
                candidate_courses=parsed_input.candidate_courses,
            )
            planner_result: CoursePlanResponse = run_course_planner(planner_input)

        else:
            if not parsed_input.completed_courses:
                output = format_query_response(
                    answer_text="I need more information before I can suggest next courses.",
                    citations=[],
                    parsed_input=parsed_input,
                    planner_result=None,
                    clarifying_questions=[
                        "Which courses have you completed so far?",
                        "If relevant, which major or program are you planning under?",
                    ],
                    assumptions_or_not_in_catalog=[
                        "Recommendations depend on your completed coursework and may also depend on program requirements."
                    ],
                )
                return QueryResponse(
                    query=payload.query,
                    parsed_input=parsed_input,
                    planner_result=None,
                    output=output,
                )

            print("USING RECOMMENDATION PLANNER")
            planner_result = run_recommendation_planner(parsed_input)

        citations = collect_citations(planner_result)
        answer = generate_answer(
            user_query=payload.query,
            planner_result=planner_result,
        )

        output = format_query_response(
            answer_text=answer,
            citations=citations,
            parsed_input=parsed_input,
            planner_result=planner_result,
        )

        return QueryResponse(
            query=payload.query,
            parsed_input=parsed_input,
            planner_result=planner_result,
            output=output,
        )

    except ValueError as e:
        print("QUERY VALUE ERROR:", repr(e))
        raise QueryServiceError(str(e)) from e
    except QueryServiceError:
        raise
    except Exception as e:
        import traceback
        print("QUERY UNEXPECTED ERROR:", repr(e))
        traceback.print_exc()
        raise QueryServiceError(f"Failed to process query: {e}") from e