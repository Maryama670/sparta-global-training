"""Pure checks shared by alert writes, evidence context and the linked-alert tool."""

from decimal import Decimal


def transactions_for_alert(alert: dict, transactions: list[dict]) -> list[dict]:
    ids = alert["transaction_ids"]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("transaction_ids must be non-empty and unique")
    indexed = {t["transaction_id"]: t for t in transactions}
    missing = set(ids) - indexed.keys()
    if missing:
        raise ValueError(f"Unknown transaction IDs: {sorted(missing)}")
    return [indexed[tid] for tid in ids]


def transaction_total(records: list[dict]) -> Decimal:
    return sum((Decimal(str(t["amount"])) for t in records), Decimal("0"))


def validate_alert_references(alert, transactions, accounts, counterparties, rules, analysts):
    records = transactions_for_alert(alert, transactions)
    account_ids = {a["account_id"] for a in accounts}
    counterparty_ids = {c["counterparty_id"] for c in counterparties}
    for transaction in records:
        if transaction["account_id"] not in account_ids:
            raise ValueError(f"Unknown account ID: {transaction['account_id']}")
        if transaction["counterparty_id"] not in counterparty_ids:
            raise ValueError(f"Unknown counterparty ID: {transaction['counterparty_id']}")
    if alert["rule_triggered"] not in {r["name"] for r in rules}:
        raise ValueError(f"Unknown detection rule: {alert['rule_triggered']}")
    # Unassigned alerts remain supported by the existing API.
    if alert.get("analyst_id") is not None and alert["analyst_id"] not in {a["analyst_id"] for a in analysts}:
        raise ValueError(f"Unknown analyst ID: {alert['analyst_id']}")
    return records


def validate_dataset(dataset: dict[str, list[dict]]) -> None:
    """Validate identities, relationships and totals without providers or I/O."""
    keys = {"accounts": "account_id", "counterparties": "counterparty_id",
            "transactions": "transaction_id", "rules": "rule_id",
            "analysts": "analyst_id", "alerts": "alert_id", "cases": "case_id"}
    for entity, key in keys.items():
        ids = [r[key] for r in dataset[entity]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate {key}")
    names = [r["name"] for r in dataset["rules"]]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate detection rule name")
    account_ids = {a["account_id"] for a in dataset["accounts"]}
    counterparty_ids = {c["counterparty_id"] for c in dataset["counterparties"]}
    for t in dataset["transactions"]:
        if t["account_id"] not in account_ids:
            raise ValueError(f"Unknown account ID: {t['account_id']}")
        if t["counterparty_id"] not in counterparty_ids:
            raise ValueError(f"Unknown counterparty ID: {t['counterparty_id']}")
    for alert in dataset["alerts"]:
        records = validate_alert_references(alert, dataset["transactions"], dataset["accounts"],
                                            dataset["counterparties"], dataset["rules"], dataset["analysts"])
        if Decimal(str(alert["amount"])) != transaction_total(records):
            raise ValueError(f"Alert {alert['alert_id']} amount does not match its transactions")
    alert_ids = {a["alert_id"] for a in dataset["alerts"]}
    analyst_ids = {a["analyst_id"] for a in dataset["analysts"]}
    for case in dataset["cases"]:
        ids = case["alert_ids"]
        if not ids or len(ids) != len(set(ids)) or not set(ids) <= alert_ids:
            raise ValueError(f"Invalid alert references in case {case['case_id']}")
        if case["analyst_id"] not in analyst_ids:
            raise ValueError(f"Unknown analyst in case {case['case_id']}")
