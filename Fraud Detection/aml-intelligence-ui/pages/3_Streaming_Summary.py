import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000")

st.title("AML Intelligence - Streaming Summary")
st.write("Select an alert and watch Claude generate an investigation summary.")

alert_id = st.number_input(
    "Select Alert ID",
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

            def stream_text():
                for chunk in response.iter_content(
                    chunk_size=64,
                    decode_unicode=True,
                ):
                    if chunk:
                        yield chunk

            st.subheader("Investigation Summary")
            st.write_stream(stream_text())

    except requests.exceptions.Timeout:
        st.error("The summary request timed out.")

    except requests.exceptions.ConnectionError:
        st.error("Cannot connect to the AML API.")

    except requests.exceptions.HTTPError as exc:
        st.error(f"API returned an error: {exc}")

    except requests.exceptions.RequestException as exc:
        st.error(f"Streaming failed: {exc}")
