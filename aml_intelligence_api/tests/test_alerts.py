from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from data import transactions
from main import app
from routers import alerts as alert_routes


@pytest.fixture
def client(monkeypatch):
    # Keep API mutations local to each test, preserving the sample records.
    monkeypatch.setattr(alert_routes, "alerts", deepcopy(alert_routes.alerts))
    with TestClient(app) as test_client:
        yield test_client


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
