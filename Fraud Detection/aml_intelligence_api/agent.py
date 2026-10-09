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
import os
from typing import cast

from anthropic.types import MessageParam, ToolUnionParam

from llm import MODEL, client


MAX_ITERATIONS = int(os.getenv("AGENT_MAX_ITERATIONS", "4"))


def ask_with_tools(question: str) -> dict:
    messages: list[MessageParam] = [
        {
            "role": "user",
            "content": question,
        }
    ]

    total_input_tokens = 0
    total_output_tokens = 0
    tool_calls_made = 0
    tools_used: list[str] = []

    tools = cast(
        list[ToolUnionParam],
        [
            SEARCH_TOOL,
            LINK_ALERTS_TOOL,
        ],
    )

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=700,
            system=AGENT_SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Claude has finished and produced an answer.
        if response.stop_reason == "end_turn":
            answer_parts = [
                block.text
                for block in response.content
                if block.type == "text"
            ]

            return {
                "answer": "\n".join(answer_parts),
                "completed": True,
                "tools_used": tools_used,
                "tool_calls_made": tool_calls_made,
                "input_tokens": total_input_tokens,
                "output_tokens": total_output_tokens,
                "stop_reason": response.stop_reason,
            }

        # Keep Claude's tool request in the conversation.
        messages.append(
            {
                "role": "assistant",
                "content": response.content,
            }
        )

        tool_blocks = [
            block
            for block in response.content
            if block.type == "tool_use"
        ]

        tool_results = []

        for tool_block in tool_blocks:
            result, is_error = execute_tool(
                tool_block.name,
                tool_block.input,
            )

            if not is_error:
                tool_calls_made += 1
                tools_used.append(tool_block.name)

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": str(result),
                    "is_error": is_error,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": tool_results,
            }
        )

    return {
        "answer": None,
        "completed": False,
        "tools_used": tools_used,
        "tool_calls_made": tool_calls_made,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "stop_reason": "max_iterations",
    }