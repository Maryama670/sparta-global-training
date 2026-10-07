from data import alerts, transactions


def get_alert(alert_id: int) -> dict | None:
    return next(
        (alert for alert in alerts if alert["alert_id"] == alert_id),
        None,
    )


def get_transactions_for_alert(alert: dict) -> list[dict]:
    transaction_ids = alert["transaction_ids"]

    return [
        transaction
        for transaction in transactions
        if transaction["transaction_id"] in transaction_ids
    ]


def get_account_ids(alert: dict) -> set[int]:
    alert_transactions = get_transactions_for_alert(alert)

    return {
        transaction["account_id"]
        for transaction in alert_transactions
    }


def get_counterparty_ids(alert: dict) -> set[int]:
    alert_transactions = get_transactions_for_alert(alert)

    return {
        transaction["counterparty_id"]
        for transaction in alert_transactions
    }


def link_alerts(alert_id: int) -> list[dict]:
    source_alert = get_alert(alert_id)

    if source_alert is None:
        raise ValueError(f"Alert {alert_id} not found")

    source_accounts = get_account_ids(source_alert)
    source_counterparties = get_counterparty_ids(source_alert)
    source_corridor = source_alert["corridor"]

    matches = []

    for candidate in alerts:
        if candidate["alert_id"] == alert_id:
            continue

        candidate_accounts = get_account_ids(candidate)
        candidate_counterparties = get_counterparty_ids(candidate)

        shared_accounts = source_accounts & candidate_accounts
        shared_counterparties = (
            source_counterparties & candidate_counterparties
        )
        same_corridor = candidate["corridor"] == source_corridor

        reasons = []

        if shared_accounts:
            reasons.append(
                f"shared account(s): {sorted(shared_accounts)}"
            )

        if shared_counterparties:
            reasons.append(
                f"shared counterparty(s): "
                f"{sorted(shared_counterparties)}"
            )

        if same_corridor:
            reasons.append(
                f"shared corridor: {source_corridor}"
            )

        if reasons:
            matches.append(
                {
                    "alert_id": candidate["alert_id"],
                    "status": candidate["status"],
                    "reasons": reasons,
                }
            )

    return matches