"""Synthetic training fixtures only; no real customer or account information.

Amounts use the exercise's common monetary unit. Currency and transaction timing
are unknown unless explicitly supplied; alert creation dates are not payment dates.
Rule labels are review indicators, not findings of crime or reporting thresholds.
"""

accounts = [
    {
        "account_id": 1,
        "customer_name": "Amina Yusuf",
        "country": "GB",
        "occupation": "Software Engineer",
        "expected_monthly_activity": 4500,
        "source_of_funds": "salary",
        "risk_level": "low",
    },
    {
        "account_id": 2,
        "customer_name": "Daniel Reed",
        "country": "GB",
        "occupation": "Property Consultant",
        "expected_monthly_activity": 12000,
        "source_of_funds": "salary_and_property_income",
        "risk_level": "medium",
    },
    {
        "account_id": 3,
        "customer_name": "Sara Khan",
        "country": "GB",
        "occupation": "Student",
        "expected_monthly_activity": 1500,
        "source_of_funds": "family_support",
        "risk_level": "medium",
    },
    {
        "account_id": 4,
        "customer_name": "Michael Jones",
        "country": "GB",
        "occupation": "Teacher",
        "expected_monthly_activity": 3200,
        "source_of_funds": "salary",
        "risk_level": "low",
    },
    {
        "account_id": 5,
        "customer_name": "Layla Ahmed",
        "country": "AE",
        "occupation": "Business Owner",
        "expected_monthly_activity": 30000,
        "source_of_funds": "business_income",
        "risk_level": "high",
    },
    {
    "account_id": 6,
    "customer_name": "No Alert Customer",
    "country": "GB",
    "occupation": "Administrator",
    "expected_monthly_activity": 2500,
    "source_of_funds": "salary",
    "risk_level": "low",
}
]
counterparties = [
    {"counterparty_id": 1, "name": "Desert Star Trading"},
    {"counterparty_id": 2, "name": "Northbridge Ltd"},
    {"counterparty_id": 3, "name": "Global Imports"},
    {"counterparty_id": 4, "name": "Westbridge Consulting"},
    {"counterparty_id": 5, "name": "Horizon Payment Services"},
]
transactions = [
    {"transaction_id": 101, "account_id": 1, "counterparty_id": 1, "amount": 3200},
    {"transaction_id": 102, "account_id": 2, "counterparty_id": 1, "amount": 3100},
    {"transaction_id": 103, "account_id": 3, "counterparty_id": 1, "amount": 2900},
    {"transaction_id": 104, "account_id": 1, "counterparty_id": 2, "amount": 15000},
    {"transaction_id": 105, "account_id": 4, "counterparty_id": 3, "amount": 250},
    {"transaction_id": 106, "account_id": 3, "counterparty_id": 4, "amount": 4200},
    {"transaction_id": 107, "account_id": 5, "counterparty_id": 1, "amount": 18000},
    {"transaction_id": 108, "account_id": 2, "counterparty_id": 5, "amount": 12500},
]

rules = [
    {"rule_id": 1, "name": "structuring"},
    {"rule_id": 2, "name": "high_value_transfer"},
    {"rule_id": 3, "name": "unusual_corridor"},
    {"rule_id": 4, "name": "rapid_movement_of_funds"},
    {"rule_id": 5, "name": "unusual_customer_activity"},
]

# These are review descriptions grounded in the unchanged guidance documents.
# None specifies a statutory reporting threshold. Timing-based detection is inactive
# because these transaction fixtures do not contain timestamps or direction.
_rule_details = [
    ("Review multiple accounts sharing a counterparty; similarity alone does not prove deliberate structuring.", "doc-008", "high", True),
    ("Review a high-value transfer against occupation, expected activity and source of funds; amount alone is not proof of suspicion.", "doc-003", "medium", True),
    ("Review an international corridor alongside customer profile and transaction purpose; a corridor is not a jurisdiction risk rating.", "doc-003", "low", True),
    ("Review rapid incoming and outgoing movement only when transaction timestamps and direction support the pattern.", "doc-007", "high", False),
    ("Review activity exceeding the customer's expected monthly activity; request missing purpose or source-of-funds evidence.", "doc-003", "medium", True),
]
for _rule, (_description, _guidance, _severity, _active) in zip(rules, _rule_details):
    _rule.update(description=_description, guidance_doc_id=_guidance,
                 threshold=None, severity=_severity, active=_active)


analysts = [
    {
        "analyst_id": 1,
        "name": "James Carter",
        "role": "Senior AML Analyst",
    },
    {
        "analyst_id": 2,
        "name": "Fatima Hassan",
        "role": "AML Analyst",
    },
    {
        "analyst_id": 3,
        "name": "Oliver Bennett",
        "role": "Financial Crime Investigator",
    },
    {
        "analyst_id": 4,
        "name": "Priya Shah",
        "role": "AML Analyst",
    },
    {
        "analyst_id": 5,
        "name": "Daniel Brooks",
        "role": "AML Team Lead",
    },
]

# Existing IDs, names and roles are preserved. Workload counts match open cases below.
for _analyst, _experience, _workload in zip(
    analysts, ["senior", "intermediate", "senior", "intermediate", "lead"], [1, 0, 1, 1, 1]
):
    _analyst.update(team="Synthetic Financial Crime Operations", experience_level=_experience,
                    active_cases=_workload, status="active")


alerts = [
    {
        "alert_id": 1,
        "transaction_ids": [101, 102, 103],
        "analyst_id": 1,
        "amount": 9200,
        "corridor": "GB->AE",
        "rule_triggered": "structuring",
        "score": 0.91,
        "status": "open",
        "risk_level": "high",
        "severity": "high",
        "created_at": "2026-10-04T10:00:00"
    },
    {
        "alert_id": 2,
        "transaction_ids": [104],
        "analyst_id": 2,
        "amount": 15000,
        "corridor": "GB->AE",
        "rule_triggered": "high_value_transfer",
        "score": 0.72,
        "status": "under_review",
        "risk_level": "medium",
        "severity": "high",
        "created_at": "2026-10-04T10:10:00"
    },
    {
        "alert_id": 3,
        "transaction_ids": [105],
        "analyst_id": 1,
        "amount": 250,
        "corridor": "GB->FR",
        "rule_triggered": "unusual_corridor",
        "score": 0.12,
        "status": "closed",
        "risk_level": "low",
        "severity": "low",
        "created_at": "2026-10-04T10:20:00"
    },
    {
        # 4,200 exceeds this student account's expected monthly activity of 1,500.
        # No claim is made about timing, intent or a reporting threshold.
        "alert_id": 4, "transaction_ids": [106], "analyst_id": 3,
        "amount": 4200, "corridor": "GB->GB",
        "rule_triggered": "unusual_customer_activity", "score": 0.68,
        "status": "open", "risk_level": "medium", "severity": "medium",
        "created_at": "2026-10-05T09:00:00",
    },
    {
        # Business-account payment below expected monthly activity; review purpose,
        # not an assertion of suspicious intent. Counterparty 1 also links Alert 1.
        "alert_id": 5, "transaction_ids": [107], "analyst_id": 4,
        "amount": 18000, "corridor": "AE->AE",
        "rule_triggered": "high_value_transfer", "score": 0.40,
        "status": "under_review", "risk_level": "medium", "severity": "medium",
        "created_at": "2026-10-05T09:15:00",
    },
    {
        # A separate review supports a fifth case without duplicating active cases.
        "alert_id": 6, "transaction_ids": [108], "analyst_id": 5,
        "amount": 12500, "corridor": "GB->GB",
        "rule_triggered": "unusual_customer_activity", "score": 0.52,
        "status": "open", "risk_level": "medium", "severity": "medium",
        "created_at": "2026-10-05T09:30:00",
    },
]

# Case records are included because Case is already a modelled entity. Closure is
# a seeded human outcome, never performed by the model or agent.
cases = [
    {"case_id": 1, "alert_ids": [1, 2], "analyst_id": 1, "status": "under_review",
     "priority": "high", "opened_at": "2026-10-04T11:00:00", "closed_at": None,
     "outcome": None, "notes": "Review shared account 1 and corridor; seek payment purpose. Timing and intent remain unknown."},
    {"case_id": 2, "alert_ids": [3], "analyst_id": 2, "status": "closed",
     "priority": "low", "opened_at": "2026-10-04T10:20:00", "closed_at": "2026-10-04T12:00:00",
     "outcome": "human_closure", "notes": "Synthetic human reviewer recorded closure; no automated closure action."},
    {"case_id": 3, "alert_ids": [4], "analyst_id": 3, "status": "open",
     "priority": "medium", "opened_at": "2026-10-05T10:00:00", "closed_at": None,
     "outcome": None, "notes": "Payment 106 exceeds expected activity; request source and purpose evidence."},
    {"case_id": 4, "alert_ids": [5], "analyst_id": 4, "status": "under_review",
     "priority": "medium", "opened_at": "2026-10-05T10:15:00", "closed_at": None,
     "outcome": None, "notes": "Review business payment 107 and shared counterparty 1; amount alone is not proof of suspicious activity."},
    {"case_id": 5, "alert_ids": [6], "analyst_id": 5, "status": "open",
     "priority": "medium", "opened_at": "2026-10-05T10:30:00", "closed_at": None,
     "outcome": None, "notes": "Payment 108 is above expected activity; seek an explanation before recommending an outcome."},
]
