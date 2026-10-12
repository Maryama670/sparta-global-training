
import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.title("AML Intelligence — Knowledge Search")
st.write("Retrieve relevant procedures without generating an AI answer.")

query = st.text_input(
    "Search AML knowledge",
    placeholder="How should structuring alerts be investigated?",
)

if st.button("Search Documents"):
    if not query.strip():
        st.warning("Enter a search question.")
    else:
        try:
            with st.spinner("Searching documents..."):
                response = requests.get(
                    f"{API_URL}/knowledge/search",
                    params={"q": query.strip()},
                    timeout=30,
                )
                response.raise_for_status()

            data = response.json()

            if isinstance(data, list):
                matches = data
            elif isinstance(data, dict):
                matches = data.get("matches", data.get("results", []))
            else:
                matches = []

            if not matches:
                st.info("No matching documents returned.")
            else:
                st.success(f"Retrieved {len(matches)} results.")

                for match in matches:
                    if not isinstance(match, dict):
                        st.write(match)
                        continue

                    st.subheader(
                        str(match.get("title", "Untitled document"))
                    )

                    st.write(
                        "Document ID:",
                        match.get("id", match.get("doc_id", "N/A")),
                    )

                    score = match.get("score")
                    if isinstance(score, (int, float)):
                        st.write("Similarity score:", round(score, 4))

                    content = match.get("text", match.get("content"))
                    if content:
                        st.write(content)

                    st.divider()

        except requests.exceptions.Timeout:
            st.error("Knowledge search timed out.")
        except requests.exceptions.RequestException as exc:
            st.error(f"Search failed: {exc}")
        except ValueError:
            st.error("Invalid JSON returned by the API.")
