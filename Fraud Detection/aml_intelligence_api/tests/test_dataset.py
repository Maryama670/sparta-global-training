from copy import deepcopy
from datetime import datetime

import pytest

import data
from documents import load_documents
from relationships import validate_dataset
from routers.accounts import AccountResponse
from routers.alerts import AlertResponse
from routers.analysts import Analyst
from routers.cases import Case
from routers.counterparties import Counterparty
from routers.rules import Rule
from routers.transactions import Transaction


MODELS = {"accounts": AccountResponse, "alerts": AlertResponse, "analysts": Analyst,
          "cases": Case, "counterparties": Counterparty, "rules": Rule,
          "transactions": Transaction}


def dataset():
    return {name: deepcopy(getattr(data, name)) for name in MODELS}


@pytest.mark.parametrize("entity", MODELS)
def test_every_entity_has_five_valid_records(entity):
    records = getattr(data, entity)
    assert len(records) >= 5
    for record in records:
        MODELS[entity].model_validate(record)


def test_all_relationships_and_alert_totals_are_valid():
    validate_dataset(dataset())


@pytest.mark.parametrize("entity,key,value", [
    ("transactions", "account_id", 99999),
    ("transactions", "counterparty_id", 99999),
    ("alerts", "transaction_ids", [99999]),
    ("alerts", "transaction_ids", []),
    ("alerts", "transaction_ids", [101, 101]),
    ("alerts", "rule_triggered", "invented_rule"),
    ("alerts", "analyst_id", 99999),
    ("alerts", "amount", 1),
    ("cases", "alert_ids", [99999]),
    ("cases", "analyst_id", 99999),
])
def test_invalid_relationships_are_rejected(entity, key, value):
    records = dataset()
    records[entity][0][key] = value
    with pytest.raises(ValueError):
        validate_dataset(records)


@pytest.mark.parametrize("entity", MODELS)
def test_duplicate_record_ids_are_rejected(entity):
    records = dataset()
    records[entity].append(deepcopy(records[entity][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        validate_dataset(records)


def test_original_records_and_relationships_remain():
    assert [a["account_id"] for a in data.accounts] == [1, 2, 3, 4, 5, 6]
    assert [(t["transaction_id"], t["account_id"], t["counterparty_id"], t["amount"])
            for t in data.transactions[:5]] == [
                (101, 1, 1, 3200), (102, 2, 1, 3100), (103, 3, 1, 2900),
                (104, 1, 2, 15000), (105, 4, 3, 250)]
    assert [(a["alert_id"], a["transaction_ids"], a["status"])
            for a in data.alerts[:3]] == [(1, [101, 102, 103], "open"),
                                        (2, [104], "under_review"), (3, [105], "closed")]
    assert not any(t["account_id"] == 6 for t in data.transactions)


def test_new_alerts_have_supported_profile_scenarios():
    accounts = {a["account_id"]: a for a in data.accounts}
    transactions = {t["transaction_id"]: t for t in data.transactions}
    alerts = {a["alert_id"]: a for a in data.alerts}
    student_payment = transactions[alerts[4]["transaction_ids"][0]]
    assert student_payment["amount"] > accounts[student_payment["account_id"]]["expected_monthly_activity"]
    business_payment = transactions[alerts[5]["transaction_ids"][0]]
    assert business_payment["amount"] < accounts[business_payment["account_id"]]["expected_monthly_activity"]
    assert business_payment["counterparty_id"] == transactions[101]["counterparty_id"]
    assert alerts[4]["rule_triggered"] == "unusual_customer_activity"
    assert alerts[5]["rule_triggered"] == "high_value_transfer"
    assert all(a["rule_triggered"] != "rapid_movement_of_funds" for a in data.alerts)
    rapid = next(r for r in data.rules if r["name"] == "rapid_movement_of_funds")
    assert rapid["active"] is False


def test_unknown_transaction_facts_stay_unknown():
    for record in data.transactions:
        transaction = Transaction.model_validate(record)
        assert transaction.timestamp is None
        assert transaction.currency is None
        assert transaction.transaction_type is None


@pytest.mark.parametrize("change", [{"amount": -1}, {"account_id": 0},
                                    {"currency": "not-a-currency"},
                                    {"timestamp": "not-a-date"}])
def test_transaction_model_still_validates_supplied_fields(change):
    with pytest.raises(ValueError):
        Transaction.model_validate({**data.transactions[0], **change})


def test_rules_reference_existing_guidance_without_invented_thresholds():
    documents = load_documents()
    assert len(documents) == 8
    assert len({d["id"] for d in documents}) == 8
    for rule in data.rules:
        assert rule["guidance_doc_id"] in {d["id"] for d in documents}
        assert rule["threshold"] is None


def test_case_chronology_and_analyst_workload():
    alert_by_id = {a["alert_id"]: a for a in data.alerts}
    for record in data.cases:
        case = Case.model_validate(record)
        assert all(case.opened_at >= datetime.fromisoformat(alert_by_id[i]["created_at"])
                   for i in case.alert_ids)
        if case.closed_at is not None:
            assert case.closed_at >= case.opened_at
            assert case.status == "closed"
        else:
            assert case.status != "closed"
    for analyst in data.analysts:
        assert analyst["active_cases"] == sum(
            c["analyst_id"] == analyst["analyst_id"] and c["status"] != "closed"
            for c in data.cases)
