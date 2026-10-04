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
        "decision": "close", "likely_typology": "false positive",
        "reasons": ["Supplied evidence reviewed"], "evidence": ["transaction 101"],
        "missing_information": [],
    }
    monkeypatch.setattr(alert_routes, "ask_claude", lambda **kwargs: {
        "text": json.dumps(recommendation),
    })
    response = client.get("/alerts/1/triage")
    assert response.status_code == 200
    assert response.json() == recommendation
    assert alert_routes.alerts == before


@pytest.mark.parametrize("text", ["not JSON", "[]", '{"decision": "invalid"}'])
def test_invalid_triage_returns_502(client, monkeypatch, text):
    monkeypatch.setattr(alert_routes, "ask_claude", lambda **kwargs: {"text": text})
    assert client.get("/alerts/1/triage").status_code == 502


def test_missing_key_does_not_block_docs(client, monkeypatch):
    monkeypatch.setattr(llm, "client", None)
    assert client.get("/docs").status_code == 200
    assert client.get("/alerts/1/summary/stream").status_code == 503
    assert client.get("/alerts/1/triage").status_code == 503


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
