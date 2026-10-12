from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from main import app
from routers import alerts as alert_routes


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AML_REVIEWER_KEY", "test-reviewer-key")
    monkeypatch.setattr(alert_routes, "closure_audit", [])
    with TestClient(app) as client:
        yield client


def close(client, alert_id=1, **changes):
    return client.post(
        f"/alerts/{alert_id}/close",
        headers={"X-Reviewer-Key": "test-reviewer-key"},
        json={"reviewer_id": 1, "reason": "Human reviewed the supplied evidence.", **changes},
    )


@pytest.mark.parametrize("key", [None, "wrong-key"])
def test_closure_requires_valid_key(client, key):
    before = deepcopy(alert_routes.alerts)
    response = client.post(
        "/alerts/1/close", headers={} if key is None else {"X-Reviewer-Key": key},
        json={"reviewer_id": 1, "reason": "Human reviewed the supplied evidence."},
    )
    assert response.status_code == 403
    assert alert_routes.alerts == before
    assert alert_routes.closure_audit == []


def test_unconfigured_authentication_fails_closed(client, monkeypatch):
    monkeypatch.delenv("AML_REVIEWER_KEY")
    assert close(client).status_code == 503
    assert alert_routes.closure_audit == []


@pytest.mark.parametrize("inactive", [False, True])
def test_reviewer_must_be_registered_and_active(client, monkeypatch, inactive):
    if inactive:
        reviewers = deepcopy(alert_routes.analysts)
        reviewers[0]["status"] = "inactive"
        monkeypatch.setattr(alert_routes, "analysts", reviewers)
    before = deepcopy(alert_routes.alerts)
    assert close(client, reviewer_id=1 if inactive else 99999).status_code == 403
    assert alert_routes.alerts == before
    assert alert_routes.closure_audit == []


@pytest.mark.parametrize("reason", ["short", " " * 20, "x" * 1001])
def test_invalid_justification_does_not_close_alert(client, reason):
    before = deepcopy(alert_routes.alerts)
    assert close(client, reason=reason).status_code == 422
    assert alert_routes.alerts == before
    assert alert_routes.closure_audit == []


def test_missing_alert_and_duplicate_closure(client):
    assert close(client, alert_id=99999).status_code == 404
    assert close(client, alert_id=3).status_code == 409
    assert alert_routes.closure_audit == []


@pytest.mark.parametrize("alert_id,previous_status", [(1, "open"), (2, "under_review")])
def test_authorised_closure_records_audit(client, alert_id, previous_status):
    response = close(client, alert_id=alert_id, reason="  Human reviewed the supplied evidence.  ")
    assert response.status_code == 200
    assert response.json()["status"] == "closed"
    record, = alert_routes.closure_audit
    assert record["alert_id"] == alert_id
    assert record["reviewer_id"] == 1
    assert record["reason"] == "Human reviewed the supplied evidence."
    assert record["previous_status"] == previous_status
    assert record["new_status"] == "closed"
    assert record["closed_at"].endswith("+00:00")
    assert "test-reviewer-key" not in str(record)
    assert close(client, alert_id=alert_id).status_code == 409
    assert len(alert_routes.closure_audit) == 1


@pytest.mark.parametrize("missing", ["reviewer_id", "reason"])
def test_closure_requires_reviewer_and_reason(client, missing):
    before = deepcopy(alert_routes.alerts)
    payload = {"reviewer_id": 1, "reason": "Human reviewed the supplied evidence."}
    del payload[missing]
    response = client.post(
        "/alerts/1/close",
        headers={"X-Reviewer-Key": "test-reviewer-key"},
        json=payload,
    )
    assert response.status_code == 422
    assert alert_routes.alerts == before
    assert alert_routes.closure_audit == []


def test_reviewer_key_does_not_bypass_ordinary_create_or_update(client):
    before = deepcopy(alert_routes.alerts)
    headers = {"X-Reviewer-Key": "test-reviewer-key"}
    payload = {
        "transaction_ids": [101], "amount": 3200, "corridor": "GB->AE",
        "rule_triggered": "structuring", "score": 0.5, "status": "closed",
        "risk_level": "medium", "severity": "medium",
    }
    assert client.post("/alerts/", headers=headers, json=payload).status_code == 403
    assert client.put("/alerts/1", headers=headers, json={"status": "closed"}).status_code == 403
    assert alert_routes.alerts == before
    assert alert_routes.closure_audit == []
