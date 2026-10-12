
import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.title("AML Intelligence — Streaming Summary")
st.write("Generate a live investigation summary for an alert.")

alert_id = st.number_input(
    "Alert ID",
    min_value=1,
    value=1,
    step=1,
)

if st.button("Generate Streaming Summary"):
    try:
        with requests.get(
            f"{API_URL}/alerts/{int(alert_id)}/summary/stream",
            stream=True,
            timeout=(10, 120),
        ) as response:

            response.raise_for_status()

            content_type = response.headers.get(
                "content-type", ""
            ).lower()

            def generate_text():
                if "text/event-stream" in content_type:
                    for line in response.iter_lines(decode_unicode=True):
                        if not line or not line.startswith("data:"):
                            continue

                        text = line[5:].lstrip()

                        if text == "[DONE]":
                            break

                        yield text
                else:
                    for chunk in response.iter_content(
                        chunk_size=64,
                        decode_unicode=True,
                    ):
                        if chunk:
                            yield chunk

            st.subheader("Investigation Summary")
            st.write_stream(generate_text())

            st.warning(
                "This is AI-generated investigation support, "
                "not a final compliance decision."
            )

    except requests.exceptions.Timeout:
        st.error("Summary request timed out.")
    except requests.exceptions.RequestException as exc:
        st.error(f"Streaming request failed: {exc}")
