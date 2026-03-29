from __future__ import annotations

from openai import OpenAI

from app.core.schemas.query import QueryParseResult


client = OpenAI()


PARSER_INSTRUCTIONS = """
You extract structured course-planning inputs from a student's natural-language question.

Return only:
- intent:
  - "eligibility_check" if the user asks about specific target course(s)
  - "recommendation" if the user asks what courses they can take next, what they are eligible for now, or asks for suggestions without naming target courses
- completed_courses: courses the student clearly says they have completed, taken, finished, passed, already did, or already have credit for
- candidate_courses: courses the student is asking about taking, enrolling in, being eligible for, or planning to take

Rules:
- Use normalized university-style course strings when possible, e.g. "CS 161", "MTH 251"
- Do not invent courses
- Do not include uncertain courses unless explicitly mentioned
- If nothing is clearly stated for a field, return an empty list
- Do not reason about prerequisite eligibility
- Do not explain anything

Negation rules:
- A course mentioned with negation such as "have not taken", "haven't taken", "did not take", "have not completed", "haven't completed", "still need", "am missing", or "not done yet" must NOT be placed in completed_courses
- A negated course must also NOT be placed in candidate_courses unless the user is explicitly asking about taking that same course

Intent rules:
- If the user names one or more courses they want to evaluate, intent = "eligibility_check"
- If the user asks what they can take next, what they are eligible for now, or asks for suggestions without naming target courses, intent = "recommendation"

Examples:

User: "Can I take CS 162 if I completed CS 161?"
intent = "eligibility_check"
completed_courses = ["CS 161"]
candidate_courses = ["CS 162"]

User: "I have not taken CS 161 yet. Can I take CS 162?"
intent = "eligibility_check"
completed_courses = []
candidate_courses = ["CS 162"]

User: "What can I take next after CS 161 and CS 162?"
intent = "recommendation"
completed_courses = ["CS 161", "CS 162"]
candidate_courses = []

User: "Which CS courses am I eligible for after completing CS 161?"
intent = "recommendation"
completed_courses = ["CS 161"]
candidate_courses = []
"""


def parse_query(query: str) -> QueryParseResult:
    completion = client.beta.chat.completions.parse(
        model="gpt-4.1-mini",
        messages=[
            {"role": "developer", "content": PARSER_INSTRUCTIONS},
            {"role": "user", "content": query},
        ],
        response_format=QueryParseResult,
    )

    message = completion.choices[0].message

    if message.refusal:
        raise ValueError(f"LLM parser refused the request: {message.refusal}")

    parsed = message.parsed
    if parsed is None:
        raise ValueError("LLM parser returned no structured result")

    return parsed