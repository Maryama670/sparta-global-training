from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import agent
from main import app
from routers import alerts as alert_routes


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(alert_routes, "alerts", deepcopy(alert_routes.alerts))
    with TestClient(app) as client:
        yield client


def valid_alert():
    return {"transaction_ids": [101], "analyst_id": 1, "amount": 3200,
            "corridor": "GB->AE", "rule_triggered": "structuring", "score": .5,
            "risk_level": "medium", "severity": "medium"}


@pytest.mark.parametrize("change", [
    {"transaction_ids": [99999]}, {"transaction_ids": []},
    {"transaction_ids": [101, 101]}, {"analyst_id": 99999},
    {"rule_triggered": "invented"}, {"amount": 42},
])
def test_create_rejects_bad_references_without_mutating(client, change):
    before = deepcopy(alert_routes.alerts)
    response = client.post("/alerts/", json={**valid_alert(), **change})
    assert response.status_code == 422
    assert alert_routes.alerts == before


@pytest.mark.parametrize("change", [
    {"transaction_ids": [99999]}, {"transaction_ids": []},
    {"analyst_id": 99999}, {"rule_triggered": "invented"},
    {"transaction_ids": None}, {"status": None}, {"amount": 42},
])
def test_update_rejects_bad_references_atomically(client, change):
    before = deepcopy(alert_routes.alerts)
    assert client.put("/alerts/1", json=change).status_code == 422
    assert alert_routes.alerts == before


def test_transaction_update_recalculates_total(client):
    response = client.put("/alerts/1", json={"transaction_ids": [104]})
    assert response.status_code == 200
    assert response.json()["amount"] == 15000


def test_nullable_analyst_assignment_remains_supported(client):
    response = client.put("/alerts/1", json={"analyst_id": None})
    assert response.status_code == 200
    assert response.json()["analyst_id"] is None


def test_case_reference_prevents_deletion_but_unlinked_alert_can_be_deleted(client):
    assert client.delete("/alerts/1").status_code == 409
    response = client.post("/alerts/", json=valid_alert())
    assert response.status_code == 201
    alert_id = response.json()["alert_id"]
    assert client.delete(f"/alerts/{alert_id}").status_code == 204
    assert client.get(f"/alerts/{alert_id}").status_code == 404


@pytest.mark.parametrize("entity,key", [("transactions", "transaction_id"),
                                        ("accounts", "account_id"),
                                        ("counterparties", "counterparty_id"),
                                        ("analysts", "analyst_id"), ("rules", "rule_id")])
def test_incomplete_stored_evidence_is_blocked_before_claude(client, monkeypatch, entity, key):
    monkeypatch.setattr(alert_routes, entity, [r for r in getattr(alert_routes, entity) if r[key] != (101 if entity == "transactions" else 1)])
    def forbidden(**kwargs):
        pytest.fail("Claude must not receive incomplete evidence")
    monkeypatch.setattr(alert_routes, "ask_claude", forbidden)
    assert client.post("/alerts/1/triage").status_code == 409


def test_linked_alerts_use_counterparties_accounts_and_corridors():
    matches = {r["alert_id"]: r for r in agent.link_alerts(1)}
    assert 1 not in matches
    assert "shared counterparty(s): [1]" in matches[5]["reasons"]
    assert "shared account(s): [3]" in matches[4]["reasons"]
    assert "shared corridor: GB->AE" in matches[2]["reasons"]


def test_missing_transaction_is_reported_as_tool_error(monkeypatch):
    monkeypatch.setattr(agent, "transactions", [t for t in agent.transactions if t["transaction_id"] != 101])
    result, error = agent.execute_tool("link_alerts", {"alert_id": 1})
    assert error is True
    assert "Unknown transaction" in result


def test_unknown_alert_and_missing_argument_are_tool_errors():
    assert agent.execute_tool("link_alerts", {"alert_id": 99999})[1] is True
    assert agent.execute_tool("link_alerts", {})[1] is True


def test_alert_filters_and_account_history_remain_compatible(client):
    rows = client.get("/alerts/", params={"status": "open", "corridor": "GB->GB"}).json()
    assert {r["alert_id"] for r in rows} == {4, 6}
    assert client.get("/accounts/3/transactions").status_code == 200
    assert {r["alert_id"] for r in client.get("/accounts/3/alerts").json()} == {1, 4}
