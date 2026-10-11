import os

import requests
import streamlit as st

API_URL = os.getenv("AML_API_URL", "http://127.0.0.1:8000")

st.title("AML Intelligence - Alert Queue")
st.write("Review suspicious activity and request AI triage recommendations.")

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

    if not alerts:
        st.info("No alerts match your filters.")
    else:
        st.write(f"Showing {len(alerts)} alerts")

        for alert in alerts:
            alert_id = alert["alert_id"]

            with st.expander(
                f"Alert {alert_id} | "
                f"{alert['risk_level'].upper()} risk | "
                f"{alert['status']}"
            ):
                st.write("Amount:", alert["amount"])
                st.write("Corridor:", alert["corridor"])
                st.write("Rule triggered:", alert["rule_triggered"])
                st.write("Risk score:", alert["score"])
                st.write("Severity:", alert["severity"])
                st.write("Transaction IDs:", alert["transaction_ids"])

                if st.button(
                    "Request AI Triage",
                    key=f"triage_{alert_id}",
                ):
                    try:
                        triage_response = requests.post(
                            f"{API_URL}/alerts/{alert_id}/triage",
                            timeout=90,
                        )
                        triage_response.raise_for_status()
                        result = triage_response.json()

                        st.subheader("AI Recommendation")
                        st.write("Decision:", result["decision"])
                        st.write("Likely typology:", result["likely_typology"])

                        st.write("Reasons:")
                        for reason in result["reasons"]:
                            st.write("-", reason)

                        st.write("Evidence:")
                        for item in result["evidence"]:
                            st.write("-", item)

                        st.write("Missing information:")
                        for item in result["missing_information"]:
                            st.write("-", item)

                        st.warning(
                            "AI recommendations are advisory only. "
                            "A human analyst must make the final decision."
                        )

                    except requests.exceptions.RequestException as exc:
                        st.error(f"Triage request failed: {exc}")

except requests.exceptions.ConnectionError:
    st.error("Cannot connect to the AML API.")

except requests.exceptions.RequestException as exc:
    st.error(f"Unable to load alerts: {exc}")
