import streamlit as st
import requests


API_URL = "http://127.0.0.1:8000"


st.title("AML Intelligence - Ask Agent")

question = st.text_area(
    "Ask an AML question",
    placeholder="Which open alerts share a counterparty, and what does our procedure say about linked structuring?"
)

alert_id = st.number_input(
    "Alert ID (optional)",
    min_value=1,
    step=1,
)


if st.button("Ask Agent"):
    if not question.strip():
        st.warning("Enter a question first.")
    else:
        payload = {
            "question": question,
            "alert_id": int(alert_id),
        }

        try:
            response = requests.post(
                f"{API_URL}/agent/ask",
                json=payload,
                timeout=60,
            )

            if response.status_code == 200:
                result = response.json()

                st.subheader("Answer")
                st.write(result["answer"])

                st.subheader("Agent details")
                st.write("Completed:", result["completed"])
                st.write("Tools used:", result["tools_used"])
                st.write("Tool calls:", result["tool_calls_made"])
                st.write("Input tokens:", result["input_tokens"])
                st.write("Output tokens:", result["output_tokens"])

                if not result["completed"]:
                    st.warning("The agent did not finish within the iteration limit.")

            else:
                st.error(
                    f"API error {response.status_code}: {response.text}"
                )

        except requests.exceptions.ConnectionError:
            st.error("The AML API is not running.")

        except requests.exceptions.RequestException as exc:
            st.error(f"Request failed: {exc}")