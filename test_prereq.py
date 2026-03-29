from app.reasoning.prereq_checker import check_prereq_from_chunk

chunk = {
    "doc_type": "course",
    "title": "Computer Science (CS) < Oregon State University",
    "source_url": "https://catalog.oregonstate.edu/courses/cs/",
    "accessed_date": "2026-03-28",
    "chunk_index": 1,
    "text": "Prerequisite: (CS 162 or CS 165) and MTH 251 with C or better.",
    "citation_label": "CS 161 | CS 161, INTRODUCTION TO COMPUTER SCIENCE I, 4 Credits",
    "section": "CS 161, INTRODUCTION TO COMPUTER SCIENCE I, 4 Credits",
    "course_code": "CS 161",
    "program_name": None,
    "catalog_year": "2025-2026",
    "metadata": {
      "section_order": 1,
      "section_parser": "course_entry",
      "subchunk_index": 0
    }
  }

result = check_prereq_from_chunk(
    target_course="CS 161",
    completed_courses=["CS 162", "MTH 251"],
    chunk=chunk,
)

print(result)