
import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="AML Intelligence",
    page_icon="🔎",
    layout="wide",
)

st.title("AML Intelligence Dashboard")
st.write("Fraud and Anti-Money Laundering investigation support")

st.info(
    "AI recommendations support investigations. "
    "Only a human analyst can make final alert decisions."
)

try:
    response = requests.get(f"{API_URL}/health", timeout=5)
    response.raise_for_status()
    st.success("AML API connected successfully.")
except requests.exceptions.RequestException:
    st.error("AML API is unavailable. Start your FastAPI server.")

st.subheader("Investigation tools")

st.page_link(
    "pages/4_Alert_Queue.py",
    label="Alert Queue — Review alerts and request triage",
    icon="🚨",
)
st.page_link(
    "pages/1_Ask.py",
    label="Ask Agent — Investigate AML questions",
    icon="🤖",
)
st.page_link(
    "pages/2_Search.py",
    label="Search — Find relevant AML procedures",
    icon="📚",
)
st.page_link(
    "pages/3_Streaming_Summary.py",
    label="Streaming Summary — Generate alert summaries",
    icon="📄",
)
