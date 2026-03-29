from pprint import pprint

from app.planning.eligibility_planner import plan_course_options

result = plan_course_options(
    completed_courses=["CS 161", "CS 162", "MTH 251"],
    candidate_courses=["CS 261", "CS 271", "CS 161"],
)

pprint(result)