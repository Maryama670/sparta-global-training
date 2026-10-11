
import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000")

st.title("AML Intelligence - Search Only")
st.write("Search AML procedures and guidance without generating an AI answer.")

query = st.text_input(
    "Search AML knowledge",
    placeholder="What is the procedure for investigating structuring?",
)

if st.button("Search Documents"):
    if not query.strip():
        st.warning("Enter a search question first.")
    else:
        try:
            response = requests.get(
                f"{API_URL}/knowledge/search",
                params={"q": query.strip()},
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                matches = data.get("matches", [])

                if not matches:
                    st.info("No matching documents found.")
                else:
                    st.success(f"Found {len(matches)} documents.")

                    for match in matches:
                        st.subheader(match["title"])
                        st.write("Document ID:", match["id"])
                        st.write(
                            "Similarity score:",
                            round(match["score"], 4),
                        )
                        st.divider()

            elif response.status_code == 503:
                st.warning(
                    "Knowledge search is unavailable. "
                    "The document index may not be built."
                )
            else:
                st.error(
                    f"API error {response.status_code}: {response.text}"
                )

        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the AML API.")

        except requests.exceptions.RequestException as exc:
            st.error(f"Search request failed: {exc}")