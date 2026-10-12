from copy import deepcopy
import json
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from data import transactions
from main import app
from routers import alerts as alert_routes
import llm


@pytest.fixture
def client(monkeypatch):
    # Keep API mutations local to each test, preserving the sample records.
    monkeypatch.setattr(alert_routes, "alerts", deepcopy(alert_routes.alerts))
    with TestClient(app) as test_client:
        yield test_client


def test_step_four_documentation(client):
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/alerts/{alert_id}/summary/stream" in schema["paths"]
    assert "/alerts/{alert_id}/triage" in schema["paths"]
    assert "TriageResponse" in schema["components"]["schemas"]


def test_streaming_summary(client, monkeypatch):
    provider = MagicMock()
    provider.messages.stream.return_value.__enter__.return_value.text_stream = iter(
        ["Review ", "the alert."]
    )
    monkeypatch.setattr(llm, "client", provider)
    response = client.get("/alerts/1/summary/stream")
    assert response.status_code == 200
    assert response.text == "Review the alert."


def test_triage_is_recommendation_only(client, monkeypatch):
    before = deepcopy(alert_routes.alerts)
    recommendation = {
        "decision": "recommend_closure", "likely_typology": "false positive",
        "reasons": ["Supplied evidence reviewed"], "evidence": ["transaction 101"],
        "missing_information": [],
    }
    monkeypatch.setattr(alert_routes, "ask_claude", lambda **kwargs: {
        "text": json.dumps(recommendation),
    })
    response = client.post("/alerts/1/triage")
    assert response.status_code == 200
    assert response.json() == recommendation
    assert alert_routes.alerts == before


@pytest.mark.parametrize("text", ["not JSON", "[]", '{"decision": "invalid"}'])
def test_invalid_triage_returns_502(client, monkeypatch, text):
    monkeypatch.setattr(alert_routes, "ask_claude", lambda **kwargs: {"text": text})
    assert client.post("/alerts/1/triage").status_code == 502


def test_missing_key_does_not_block_docs(client, monkeypatch):
    monkeypatch.setattr(llm, "client", None)
    assert client.get("/docs").status_code == 200
    assert client.get("/alerts/1/summary/stream").status_code == 503
    assert client.post("/alerts/1/triage").status_code == 503


def test_list_and_get_alert_cover_multiple_accounts(client):
    response = client.get("/alerts/")
    assert response.status_code == 200
    response = client.get("/alerts/1")
    assert response.status_code == 200
    alert = response.json()
    assert "account_id" not in alert
    account_ids = {
        transaction["account_id"]
        for transaction in transactions
        if transaction["transaction_id"] in alert["transaction_ids"]
    }
    assert account_ids == {1, 2, 3}


def test_create_unassigned_alert_then_update_transactions(client, monkeypatch):
    monkeypatch.setattr(alert_routes, "alerts", [])
    response = client.post("/alerts/", json={
        "transaction_ids": [101, 102, 103],
        "amount": 9200,
        "corridor": "GB->AE",
        "rule_triggered": "structuring",
        "score": 0.91,
        "risk_level": "high",
        "severity": "high",
    })
    assert response.status_code == 201
    alert = response.json()
    assert alert["alert_id"] == 1
    assert alert["analyst_id"] is None
    assert "account_id" not in alert

    response = client.put("/alerts/1", json={"transaction_ids": [104]})
    assert response.status_code == 200
    assert response.json()["transaction_ids"] == [104]
def test_summary_returns_text_and_token_counts(client, monkeypatch):
    monkeypatch.setattr(
        llm,
        "ask_claude",
        lambda **kwargs: {
            "text": "Test AML alert summary",
            "input_tokens": 120,
            "output_tokens": 45,
        },
    )

    response = client.post("/alerts/1/summary")

    assert response.status_code == 200

    body = response.json()

    assert body["summary"] == "Test AML alert summary"
    assert body["input_tokens"] == 120
    assert body["output_tokens"] == 45


def test_summary_timeout_returns_504(client, monkeypatch):
    from fastapi import HTTPException

    def fake_timeout(**kwargs):
        raise HTTPException(
            status_code=504,
            detail="Claude request timed out",
        )

    monkeypatch.setattr(
        llm,
        "ask_claude",
        fake_timeout,
    )

    response = client.post("/alerts/1/summary")

    assert response.status_code == 504
    assert response.json()["detail"] == "Claude request timed out"


def test_summary_prompt_requires_timing_evidence():
    prompt = alert_routes.SUMMARY_SYSTEM_PROMPT.lower()
    assert "transaction timing cannot be established" in prompt
    assert "created_at field is not a transaction timestamp" in prompt
    assert "not proven intent" in prompt


def test_streaming_summary_receives_safety_prompt(client, monkeypatch):
    captured = {}

    def fake_stream(system_prompt, user_message):
        captured["system_prompt"] = system_prompt
        captured["context"] = json.loads(user_message)
        yield "Transaction timing cannot be established."

    monkeypatch.setattr(alert_routes, "stream_claude", fake_stream)
    response = client.get("/alerts/1/summary/stream")
    assert response.status_code == 200
    assert captured["system_prompt"] == alert_routes.SUMMARY_SYSTEM_PROMPT
    assert captured["context"]["alert"]["alert_id"] == 1
    assert response.text == "Transaction timing cannot be established."


def test_regular_summary_receives_same_safety_prompt(client, monkeypatch):
    captured = {}

    def fake_summary(system_prompt, user_message):
        captured["system_prompt"] = system_prompt
        captured["context"] = json.loads(user_message)
        return {"text": "Summary", "input_tokens": 10, "output_tokens": 2}

    monkeypatch.setattr(llm, "ask_claude", fake_summary)
    response = client.post("/alerts/1/summary")
    assert response.status_code == 200
    assert captured["system_prompt"] == alert_routes.SUMMARY_SYSTEM_PROMPT
    assert captured["context"]["alert"]["alert_id"] == 1


def test_alert_context_includes_counterparties():
    context = alert_routes.get_alert_context(1)
    assert "counterparties" in context
    counterparties = context["counterparties"]
    assert any(
        cp["counterparty_id"] == 1
        and cp["name"] == "Desert Star Trading"
        for cp in counterparties
    )


def test_ordinary_update_cannot_close_alert(client):
    """Ordinary API updates must not close alerts."""
    before = deepcopy(alert_routes.alerts)
    response = client.put("/alerts/1", json={"status": "closed"})
    assert response.status_code == 403
    assert alert_routes.alerts == before


def test_ordinary_update_can_mark_alert_under_review(client):
    """Legitimate investigation updates must still work."""
    response = client.put("/alerts/1", json={"status": "under_review"})
    assert response.status_code == 200
    assert response.json()["status"] == "under_review"


def test_cannot_create_closed_alert(client):
    """Creating an already-closed alert must be rejected."""
    before = deepcopy(alert_routes.alerts)
    payload = {
        "transaction_ids": [101, 102, 103],
        "amount": 9200,
        "corridor": "GB->AE",
        "rule_triggered": "structuring",
        "score": 0.91,
        "status": "closed",
        "risk_level": "high",
        "severity": "high",
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 403
    assert alert_routes.alerts == before


def test_new_alert_defaults_to_open(client):
    """New alerts should default to open when status is omitted."""
    payload = {
        "transaction_ids": [101, 102, 103],
        "amount": 9200,
        "corridor": "GB->AE",
        "rule_triggered": "structuring",
        "score": 0.91,
        "risk_level": "high",
        "severity": "high",
    }
    response = client.post("/alerts/", json=payload)
    assert response.status_code == 201
    assert response.json()["status"] == "open"
