
import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.title("AML Intelligence — Ask Agent")

st.warning(
    "⚠️ CAUTION — Avoid vague investigation questions.\n\n"
    "Vague or incomplete questions may lead to irrelevant evidence, "
    "misleading conclusions, or unsupported AI recommendations.\n\n"
    "Be specific: include an Alert ID, transaction pattern, "
    "suspicious activity, or investigation objective.\n\n"
    "Example: For Alert 1, identify linked counterparties "
    "and explain the structuring investigation procedure."
)
st.caption(
    "Good prompts: 'For Alert 1, find open linked alerts and explain each actual "
    "relationship using link_alerts; use search_knowledge_base for structuring guidance.' "
    "Or: 'What does doc-004 require before recommending an alert outcome?'"
)

question = st.text_area(
    "Ask an AML question",
    placeholder="Which open alerts share a counterparty?",
)

use_alert_id = st.checkbox("Ask about a specific alert")

alert_id = None
if use_alert_id:
    alert_id = st.number_input(
        "Alert ID",
        min_value=1,
        value=1,
        step=1,
    )

if st.button("Ask Agent"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        payload = {"question": question.strip()}

        if use_alert_id:
            payload["alert_id"] = int(alert_id)

        try:
            with st.spinner("Investigating..."):
                response = requests.post(
                    f"{API_URL}/agent/ask",
                    json=payload,
                    timeout=90,
                )
                response.raise_for_status()

            result = response.json()

            st.subheader("Agent Answer")
            st.write(result.get("answer") or "No answer returned.")

            st.subheader("Agent Details")
            st.write("Completed:", result.get("completed", "Unknown"))
            st.write("Tools used:", result.get("tools_used", []))
            st.write("Tool calls:", result.get("tool_calls_made", 0))
            st.write("Input tokens:", result.get("input_tokens", "N/A"))
            st.write("Output tokens:", result.get("output_tokens", "N/A"))

            if result.get("completed") is False:
                st.warning("Agent stopped before completing.")

        except requests.exceptions.Timeout:
            st.error("Agent request timed out.")
        except requests.exceptions.RequestException as exc:
            st.error(f"Agent request failed: {exc}")
        except ValueError:
            st.error("The API returned an invalid JSON response.")
