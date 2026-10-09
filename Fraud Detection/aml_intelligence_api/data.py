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
]

transactions = [
    {"transaction_id": 101, "account_id": 1, "counterparty_id": 1, "amount": 3200},
    {"transaction_id": 102, "account_id": 2, "counterparty_id": 1, "amount": 3100},
    {"transaction_id": 103, "account_id": 3, "counterparty_id": 1, "amount": 2900},
    {"transaction_id": 104, "account_id": 1, "counterparty_id": 2, "amount": 15000},
    {"transaction_id": 105, "account_id": 4, "counterparty_id": 3, "amount": 250},
]

rules = [
    {"rule_id": 1, "name": "structuring"},
    {"rule_id": 2, "name": "high_value_transfer"},
    {"rule_id": 3, "name": "unusual_corridor"},
]



###below is 3 alerts we need 15 


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
]