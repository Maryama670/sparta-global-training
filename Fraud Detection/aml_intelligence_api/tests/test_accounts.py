
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from main import app
from routers import accounts as account_routes


@pytest.fixture
def client(monkeypatch):
    # Keep test changes separate from original account records.
    monkeypatch.setattr(
        account_routes,
        "accounts",
        deepcopy(account_routes.accounts),
    )

    with TestClient(app) as test_client:
        yield test_client


def test_list_accounts(client):
    response = client.get("/accounts/")
    assert response.status_code == 200
    assert len(response.json()) >= 5


def test_account_filters(client):
    response = client.get(
        "/accounts/",
        params={"country": "GB", "risk_level": "low"},
    )

    assert response.status_code == 200

    for account in response.json():
        assert account["country"] == "GB"
        assert account["risk_level"] == "low"


def test_create_and_read_account(client):
    new_account = {
        "customer_name": "Test Customer",
        "country": "GB",
        "occupation": "Accountant",
        "expected_monthly_activity": 5000,
        "source_of_funds": "salary",
        "risk_level": "medium",
    }

    response = client.post("/accounts/", json=new_account)

    assert response.status_code == 201
    account_id = response.json()["account_id"]

    response = client.get(f"/accounts/{account_id}")

    assert response.status_code == 200
    assert response.json()["customer_name"] == "Test Customer"


def test_update_account(client):
    response = client.put(
        "/accounts/1",
        json={"risk_level": "high"},
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "high"


def test_delete_account_without_transactions(client):
    response = client.delete("/accounts/6")

    assert response.status_code == 204
    assert client.get("/accounts/6").status_code == 404


def test_prevent_deleting_account_with_transactions(client):
    response = client.delete("/accounts/1")

    assert response.status_code == 409
    assert client.get("/accounts/1").status_code == 200


def test_reject_negative_monthly_activity(client):
    response = client.post(
        "/accounts/",
        json={
            "customer_name": "Invalid Test",
            "country": "GB",
            "occupation": "Teacher",
            "expected_monthly_activity": -500,
            "source_of_funds": "salary",
            "risk_level": "low",
        },
    )

    assert response.status_code == 422


def test_unknown_account_returns_404(client):
    response = client.get("/accounts/99999")
    assert response.status_code == 404
def test_reject_null_customer_name(client):
    response = client.put(
        "/accounts/1",
        json={"customer_name": None},
    )

    assert response.status_code == 422
    assert client.get("/accounts/1").json()["customer_name"] == "Amina Yusuf"