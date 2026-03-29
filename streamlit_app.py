import json
from typing import Any, Dict, List

import requests
import streamlit as st


st.set_page_config(
    page_title="Course Planning Assistant Demo",
    page_icon="🎓",
    layout="wide",
)

DEFAULT_API_BASE = "http://localhost:8000"


def safe_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def post_json(url: str, payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    resp = requests.post(url, json=payload, timeout=timeout)
    resp.raise_for_status()
    try:
        return resp.json()
    except Exception:
        return {"raw_text": resp.text}


def normalize_to_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def extract_field(data: Dict[str, Any], *possible_keys: str) -> Any:
    for key in possible_keys:
        if key in data and data[key] not in (None, "", []):
            return data[key]
    return None


def render_citations(citations: Any) -> None:
    items = normalize_to_list(citations)
    if not items:
        st.info("No citations returned.")
        return

    for i, c in enumerate(items, start=1):
        if isinstance(c, dict):
            label = c.get("citation_label") or c.get("label") or f"Citation {i}"
            section = c.get("section")
            url = c.get("source_url") or c.get("url")
            chunk_id = c.get("chunk_id")

            lines = [f"**{label}**"]
            if section:
                lines.append(f"Section: {section}")
            if url:
                lines.append(f"Source: [{url}]({url})")
            if chunk_id:
                lines.append(f"Chunk: `{chunk_id}`")

            st.markdown("\n\n".join(lines))
        else:
            st.markdown(f"- {c}")


def render_plan_like(value: Any) -> None:
    if value is None:
        st.info("No content returned.")
        return

    if isinstance(value, list):
        for idx, item in enumerate(value, start=1):
            with st.expander(f"Item {idx}", expanded=True):
                if isinstance(item, dict):
                    st.json(item)
                else:
                    st.write(item)
        return

    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (list, dict)):
                with st.expander(k.replace("_", " ").title(), expanded=True):
                    st.json(v)
            else:
                st.write(f"**{k}**: {v}")
        return

    st.write(value)


def render_structured_output(output_block: Dict[str, Any]) -> None:
    answer_or_plan = extract_field(
        output_block, "answer_or_plan", "answer", "plan", "result", "response"
    )
    why = extract_field(output_block, "why", "reasoning", "explanation")
    citations = extract_field(output_block, "citations", "sources", "evidence")
    clarifying_questions = extract_field(
        output_block, "clarifying_questions", "questions_to_clarify", "follow_up_questions"
    )
    assumptions = extract_field(
        output_block,
        "assumptions_or_not_in_catalog",
        "assumptions",
        "not_in_catalog",
        "limitations",
    )

    left, right = st.columns([2, 1])

    with left:
        st.subheader("Answer / Plan")
        if isinstance(answer_or_plan, (dict, list)):
            render_plan_like(answer_or_plan)
        elif answer_or_plan is not None:
            st.write(answer_or_plan)
        else:
            st.info("No answer_or_plan field found. Showing output block below.")
            st.json(output_block)

        st.subheader("Why")
        if why is None:
            st.info("No explanation returned.")
        elif isinstance(why, (dict, list)):
            st.json(why)
        else:
            st.write(why)

        st.subheader("Clarifying Questions")
        questions = normalize_to_list(clarifying_questions)
        if questions:
            for q in questions:
                st.markdown(f"- {q}")
        else:
            st.info("No clarifying questions.")

        st.subheader("Assumptions / Not in Catalog")
        if assumptions is None:
            st.info("No assumptions returned.")
        elif isinstance(assumptions, (dict, list)):
            st.json(assumptions)
        else:
            st.write(assumptions)

    with right:
        st.subheader("Citations")
        render_citations(citations)


def render_query_response(data: Dict[str, Any]) -> None:
    st.subheader("Parsed Input")
    parsed_input = data.get("parsed_input")
    if parsed_input is not None:
        st.json(parsed_input)
    else:
        st.info("No parsed_input field returned.")

    st.divider()

    st.subheader("Final Output")
    output_block = data.get("output")
    if isinstance(output_block, dict):
        render_structured_output(output_block)
    elif output_block is not None:
        st.write(output_block)
    else:
        st.info("No output field returned.")
        st.json(data)

    with st.expander("Raw JSON Response"):
        st.json(data)


def render_plan_response(data: Dict[str, Any]) -> None:
    st.subheader("Plan Summary")
    summary = data.get("summary")

    if isinstance(summary, dict):
        # If summary itself follows your spec, render it nicely
        if any(
            key in summary
            for key in [
                "answer_or_plan",
                "answer",
                "plan",
                "why",
                "citations",
                "clarifying_questions",
                "assumptions_or_not_in_catalog",
            ]
        ):
            render_structured_output(summary)
        else:
            st.json(summary)
    elif summary is not None:
        st.write(summary)
    else:
        st.info("No summary field returned.")
        st.json(data)

    # Show any other top-level keys too
    extra_keys = {k: v for k, v in data.items() if k != "summary"}
    if extra_keys:
        with st.expander("Additional Response Fields"):
            st.json(extra_keys)

    with st.expander("Raw JSON Response"):
        st.json(data)


st.title("🎓 Agentic RAG Course Planning Assistant")
st.caption(
    "Thin Streamlit demo over your FastAPI backend. "
)

with st.sidebar:
    st.header("Backend")
    api_base = st.text_input("API Base URL", value=DEFAULT_API_BASE)
    query_endpoint = st.text_input("Query Endpoint", value="/query")
    plan_endpoint = st.text_input("Plan Endpoint", value="/plan/courses")

    st.divider()
    st.header("Notes")
    st.markdown(
        """
- This app is only a UI layer.
- All reasoning stays in the backend.
- Demo should clearly show citations and safe abstention.
        """
    )

mode = st.radio(
    "Choose Demo Mode",
    ["Ask the Assistant", "Eligibility", "Recommendation"],
    horizontal=True,
)

st.divider()

if mode == "Ask the Assistant":
    st.subheader("Free-form Query")

    sample_queries = [
        "Can I take CS 261 if I completed CS 161 and CS 162?",
        "What do I need before enrolling in Database Systems?",
        "Suggest a next-term plan for a CS student who completed CS 161, CS 162, and MTH 251.",
        "Is this course offered in Winter term?",
    ]

    selected = st.selectbox("Sample Prompt", options=["Custom"] + sample_queries)

    if selected == "Custom":
        query_text = st.text_area("Enter your query", height=140)
    else:
        query_text = st.text_area("Enter your query", value=selected, height=140)

    if st.button("Ask", use_container_width=True):
        payload = {"query": query_text}

        try:
            with st.spinner("Calling /query ..."):
                data = post_json(f"{api_base}{query_endpoint}", payload)

            st.success("Response received.")
            render_query_response(data)

        except requests.HTTPError as e:
            st.error(f"HTTP error: {e}")
            if e.response is not None:
                st.code(e.response.text)
        except Exception as e:
            st.error(f"Request failed: {e}")

elif mode == "Eligibility":
    st.subheader("Eligibility Check")

    st.info(
        "Use this mode only if your /plan/courses request schema supports structured planning inputs. "
        "Otherwise use Ask the Assistant for the demo."
    )

    col1, col2 = st.columns(2)

    with col1:
        completed_courses_text = st.text_area(
            "Completed Courses (comma-separated)",
            value="CS 161, CS 162",
            height=100,
        )
        grades_json_text = st.text_area(
            "Optional Grades JSON",
            value='{"CS 161": "A", "CS 162": "B"}',
            height=100,
        )

    with col2:
        candidate_course = st.text_input("Candidate Course", value="CS 261")
        catalog_year = st.text_input("Catalog Year (optional)", value="2025-2026")
        program_name = st.text_input("Program / Major (optional)", value="Computer Science")

    if st.button("Run Eligibility Check", use_container_width=True):
        completed_courses = [
            c.strip() for c in completed_courses_text.split(",") if c.strip()
        ]
        grades = safe_json_loads(grades_json_text) or {}

        # Adjust these keys if your CoursePlanRequest uses different names
        payload = {
            "mode": "eligibility",
            "completed_courses": completed_courses,
            "candidate_courses": [candidate_course] if candidate_course else [],
            "grades": grades,
            "catalog_year": catalog_year or None,
            "program_name": program_name or None,
        }

        try:
            with st.spinner("Calling /plan/courses ..."):
                data = post_json(f"{api_base}{plan_endpoint}", payload)

            st.success("Response received.")
            render_plan_response(data)

        except requests.HTTPError as e:
            st.error(f"HTTP error: {e}")
            if e.response is not None:
                st.code(e.response.text)
                st.warning(
                    "If this fails due to schema mismatch, use Ask the Assistant mode for the demo "
                    "or replace these payload keys with your exact CoursePlanRequest fields."
                )
        except Exception as e:
            st.error(f"Request failed: {e}")

else:
    st.subheader("Recommendation")

    st.info(
        "Use this mode if your /plan/courses schema supports structured planning requests."
    )

    col1, col2 = st.columns(2)

    with col1:
        completed_courses_text = st.text_area(
            "Completed Courses (comma-separated)",
            value="CS 161, CS 162, MTH 251",
            height=100,
        )
        target_program = st.text_input("Target Program / Major", value="Computer Science")
        target_term = st.text_input("Target Term", value="Fall")

    with col2:
        max_courses = st.number_input("Max Courses", min_value=1, max_value=8, value=4)
        max_credits = st.number_input("Max Credits", min_value=1, max_value=24, value=16)
        catalog_year = st.text_input("Catalog Year (optional)", value="2025-2026")

    if st.button("Generate Recommendation", use_container_width=True):
        completed_courses = [
            c.strip() for c in completed_courses_text.split(",") if c.strip()
        ]

        # Adjust these keys if your CoursePlanRequest uses different names
        payload = {
            "mode": "recommendation",
            "completed_courses": completed_courses,
            "target_program": target_program,
            "target_term": target_term,
            "max_courses": int(max_courses),
            "max_credits": int(max_credits),
            "catalog_year": catalog_year or None,
        }

        try:
            with st.spinner("Calling /plan/courses ..."):
                data = post_json(f"{api_base}{plan_endpoint}", payload)

            st.success("Response received.")
            render_plan_response(data)

        except requests.HTTPError as e:
            st.error(f"HTTP error: {e}")
            if e.response is not None:
                st.code(e.response.text)
                st.warning(
                    "If this fails due to schema mismatch, replace these payload keys with your exact "
                    "CoursePlanRequest fields."
                )
        except Exception as e:
            st.error(f"Request failed: {e}")