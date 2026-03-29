from __future__ import annotations

from typing import List

from openai import OpenAI

from app.core.schemas.planning import Citation, CoursePlanResponse, PlannerCourseResult

client = OpenAI()


SINGLE_COURSE_ANSWER_INSTRUCTIONS = """
You are formatting a grounded course-planning response.

You will receive:
- the user's original question
- a deterministic planner result for one course

Your job is to write a clear, concise answer based ONLY on the planner result.

Rules:
- Do not invent prerequisites, policies, or eligibility rules
- Do not contradict the planner result
- If the planner says eligible, say the student is eligible
- If the planner says not_eligible, say the student is not currently eligible
- If the planner says need_more_info, say more information is needed
- When not eligible, clearly state what the student is missing and how they can become eligible
- Keep the answer concise and user-facing
- Do not mention internal implementation details like parser, JSON, debug fields, or system design
- Do not add citations inline
"""


def flatten_course_results(planner_result: CoursePlanResponse) -> List[PlannerCourseResult]:
    return (
        planner_result.eligible_now
        + planner_result.not_eligible
        + planner_result.need_more_info
    )


def collect_citations(planner_result: CoursePlanResponse) -> List[Citation]:
    seen = set()
    citations: List[Citation] = []

    for item in flatten_course_results(planner_result):
        for citation in item.citations:
            key = (
                citation.citation_label,
                citation.source_url,
                citation.catalog_year,
                citation.section,
            )
            if key not in seen:
                seen.add(key)
                citations.append(citation)

    return citations


def generate_multi_course_answer_deterministic(
    *,
    planner_result: CoursePlanResponse,
) -> str:
    lines = ["Here’s your eligibility summary:"]

    for item in flatten_course_results(planner_result):
        if item.decision == "eligible":
            lines.append(f"- {item.course_code}: You are eligible.")
        elif item.decision == "not_eligible":
            if item.next_steps:
                lines.append(
                    f"- {item.course_code}: You are not currently eligible. {item.next_steps[0]}"
                )
            else:
                lines.append(
                    f"- {item.course_code}: You are not currently eligible because you are missing one or more prerequisites."
                )
        else:
            lines.append(
                f"- {item.course_code}: More information is needed to determine eligibility."
            )

    return "\n".join(lines)

def generate_recommendation_answer(planner_result: CoursePlanResponse) -> str:
    if not planner_result.eligible_now:
        return "I could not find any clearly eligible next courses in the current recommendation pool."

    course_codes = [item.course_code for item in planner_result.eligible_now]
    joined = ", ".join(course_codes)

    return (
        "Based on the courses you’ve completed, these look like the most sensible next CS courses: "
        f"{joined}."
    )

def generate_single_course_answer(
    *,
    user_query: str,
    planner_result: CoursePlanResponse,
) -> str:
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0,
        messages=[
            {"role": "developer", "content": SINGLE_COURSE_ANSWER_INSTRUCTIONS},
            {
                "role": "user",
                "content": (
                    f"User query:\n{user_query}\n\n"
                    f"Planner result:\n{planner_result.model_dump_json(indent=2)}"
                ),
            },
        ],
    )

    content = completion.choices[0].message.content
    if not content:
        raise ValueError("LLM answer generator returned empty content")

    return content.strip()


def generate_answer(
    *,
    user_query: str,
    planner_result: CoursePlanResponse,
) -> str:
    all_results = flatten_course_results(planner_result)

    if not all_results:
        return "I could not evaluate any candidate courses from your query."

    # Recommendation-style case: many eligible results
    if len(planner_result.eligible_now) > 1:
        return generate_recommendation_answer(planner_result)

    # Single-course style
    if len(all_results) == 1:
        return generate_single_course_answer(
            user_query=user_query,
            planner_result=planner_result,
        )

    # Multi-course eligibility summary
    lines = ["Here’s your eligibility summary:"]
    for item in all_results:
        if item.decision == "eligible":
            lines.append(f"- {item.course_code}: You are eligible.")
        elif item.decision == "not_eligible":
            if item.next_steps:
                lines.append(
                    f"- {item.course_code}: You are not currently eligible. {item.next_steps[0]}"
                )
            else:
                lines.append(
                    f"- {item.course_code}: You are not currently eligible because you are missing one or more prerequisites."
                )
        else:
            lines.append(
                f"- {item.course_code}: More information is needed to determine eligibility."
            )

    return "\n".join(lines)