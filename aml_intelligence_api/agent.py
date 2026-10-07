import knowledge_store as knowledge
from data import alerts, transactions
from typing import cast
from anthropic.types import MessageParam, ToolUnionParam

from llm import MODEL, client

AGENT_SYSTEM_PROMPT = (
    "You are an AML operations assistant with access to tools. "
    "Use the tools whenever you need evidence. Do not guess. "
    "Use search_knowledge_base for AML procedures and guidance. "
    "Use link_alerts when you need to identify related alerts. "
    "Cite document IDs when using knowledge-base evidence. "
    "You may recommend escalate, request information, or recommend closure, "
    "but you must never change an alert's status."
)


SEARCH_TOOL = {
    "name": "search_knowledge_base",
    "description": "Search AML procedures, typologies and guidance.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "AML knowledge search query",
            }
        },
        "required": ["query"],
    },
}


LINK_ALERTS_TOOL = {
    "name": "link_alerts",
    "description": (
        "Find other alerts related to a given alert through shared "
        "accounts, counterparties or corridors."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "alert_id": {
                "type": "integer",
                "description": "Alert ID to compare against other alerts",
            }
        },
        "required": ["alert_id"],
    },
}
def execute_tool(name: str, tool_input: dict) -> tuple[object, bool]:
    try:
        if name == "search_knowledge_base":
            query = tool_input.get("query")

            if not query:
                return 'Error: missing required field "query"', True

            return search_knowledge_base(query), False

        if name == "link_alerts":
            alert_id = tool_input.get("alert_id")

            if alert_id is None:
                return 'Error: missing required field "alert_id"', True

            return link_alerts(alert_id), False

        return f"Unknown tool: {name}", True

    except (RuntimeError, ValueError) as exc:
        return f"Error: {exc}", True
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
                f"shared counterparty(s): {sorted(shared_counterparties)}"
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


def search_knowledge_base(query: str) -> list[dict]:
    """Search the AML knowledge base for relevant procedures and guidance."""

    results = knowledge.search(query, top_k=3)

    return [
        {
            "id": result["id"],
            "title": result["title"],
            "score": result["score"],
            "text": result["text"],
        }
        for result in results
    ]