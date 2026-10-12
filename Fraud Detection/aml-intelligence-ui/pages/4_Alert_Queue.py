
import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000").rstrip("/")

st.title("AML Intelligence — Alert Queue")
st.write("Review suspicious activity and request AI triage.")

status = st.selectbox(
    "Filter by status",
    ["All", "open", "under_review", "closed"],
)

corridor = st.text_input(
    "Filter by corridor",
    placeholder="GB->AE",
)

params = {}

if status != "All":
    params["status"] = status

if corridor.strip():
    params["corridor"] = corridor.strip()

try:
    response = requests.get(
        f"{API_URL}/alerts/",
        params=params,
        timeout=15,
    )
    response.raise_for_status()

    alerts = response.json()

    if not isinstance(alerts, list):
        st.error("Unexpected alert response format.")
        st.stop()

    st.metric("Alerts displayed", len(alerts))

    if not alerts:
        st.info("No alerts match your filters.")

    for alert in alerts:
        alert_id = alert.get("alert_id")

        if alert_id is None:
            st.warning("An alert is missing its ID.")
            continue

        risk_level = str(alert.get("risk_level", "unknown"))
        alert_status = str(alert.get("status", "unknown"))

        with st.expander(
            f"Alert {alert_id} | "
            f"{risk_level.upper()} risk | {alert_status}"
        ):
            st.write("Amount:", alert.get("amount", "N/A"))
            st.write("Corridor:", alert.get("corridor", "N/A"))
            st.write("Rule:", alert.get("rule_triggered", "N/A"))
            st.write("Risk score:", alert.get("score", "N/A"))
            st.write("Severity:", alert.get("severity", "N/A"))
            st.write("Transactions:", alert.get("transaction_ids", []))

            if st.button("Request AI Triage", key=f"triage_{alert_id}"):
                try:
                    with st.spinner("Analysing alert..."):
                        triage_response = requests.post(
                            f"{API_URL}/alerts/{alert_id}/triage",
                            timeout=90,
                        )
                        triage_response.raise_for_status()

                    result = triage_response.json()

                    st.subheader("AI Recommendation")
                    st.write("Decision:", result.get("decision", "Unknown"))
                    st.write(
                        "Likely typology:",
                        result.get("likely_typology", "Unknown"),
                    )

                    st.markdown("**Reasons**")
                    for reason in result.get("reasons", []):
                        st.write("-", reason)

                    st.markdown("**Evidence**")
                    for item in result.get("evidence", []):
                        st.write("-", item)

                    st.markdown("**Missing Information**")
                    for item in result.get("missing_information", []):
                        st.write("-", item)

                    st.warning(
                        "AI recommendations are advisory only. "
                        "A human analyst must make the final decision."
                    )

                except requests.exceptions.Timeout:
                    st.error("Triage request timed out.")
                except requests.exceptions.RequestException as exc:
                    st.error(f"Triage request failed: {exc}")
                except ValueError:
                    st.error("Triage returned invalid JSON.")

except requests.exceptions.Timeout:
    st.error("Alert request timed out.")
except requests.exceptions.RequestException as exc:
    st.error(f"Cannot load alerts: {exc}")
except ValueError:
    st.error("The alerts endpoint returned invalid JSON.")
