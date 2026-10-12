from datetime import datetime, timezone
import os
import secrets
from typing import Literal
import json
import llm 
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from data import accounts, alerts, transactions, counterparties, rules, analysts, cases
from relationships import validate_alert_references, transaction_total
from llm import ask_claude, stream_claude


router = APIRouter(
    prefix="/alerts",
    tags=["alerts"]
)

reviewer_header = APIKeyHeader(name="X-Reviewer-Key", auto_error=False)
# Prototype audit storage, held in memory.
closure_audit: list[dict] = []


def verify_reviewer_key(supplied_key: str | None = Security(reviewer_header)):
    expected_key = os.getenv("AML_REVIEWER_KEY", "")
    if not expected_key:
        raise HTTPException(
            status_code=503,
            detail="Reviewer authentication is not configured",
        )
    if not supplied_key or not secrets.compare_digest(
        supplied_key.encode("utf-8"), expected_key.encode("utf-8")
    ):
        raise HTTPException(status_code=403, detail="Reviewer credential is invalid")
    return True


#Create a helper first so you can gather the complete alert context:


def get_alert_context(alert_id: int):
    alert = next(
        (a for a in alerts if a["alert_id"] == alert_id),
        None
    )

    if alert is None:
        raise HTTPException(
            status_code=404,
            detail="Alert not found"
        )

    try:
        alert_transactions = validate_alert_references(
            alert, transactions, accounts, counterparties, rules, analysts
        )
    except ValueError as exc:
        # Never send partial, silently truncated evidence to the model.
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    account_ids = {
        transaction["account_id"]
        for transaction in alert_transactions
    }

    alert_accounts = [
        account
        for account in accounts
        if account["account_id"] in account_ids
    ]

    counterparty_ids = {
        transaction["counterparty_id"]
        for transaction in alert_transactions
    }
    alert_counterparties = [
        counterparty
        for counterparty in counterparties
        if counterparty["counterparty_id"] in counterparty_ids
    ]

    return {
        "alert": alert,
        "accounts": alert_accounts,
        "transactions": alert_transactions,
        "counterparties": alert_counterparties,
    }

SUMMARY_SYSTEM_PROMPT = (
    "You are an AML investigation assistant. "
    "Summarise only facts supported by the supplied alert records. "
    "Never invent transaction dates, timing, frequency, velocity, "
    "or reporting thresholds. "
    "The alert created_at field is not a transaction timestamp. "
    "If transactions lack timestamps, explicitly state that "
    "transaction timing cannot be established. "
    "Treat structuring as a possible typology, not proven intent. "
    "Do not claim that reporting thresholds were deliberately avoided. "
    "Identify important missing evidence. "
    "Do not make a final compliance decision."
)


@router.post("/{alert_id}/summary")
def summarise_alert(alert_id: int):
    context = get_alert_context(alert_id)

    system_prompt = SUMMARY_SYSTEM_PROMPT

    user_message = json.dumps(jsonable_encoder(context))

    result = llm.ask_claude(
        system_prompt=system_prompt,
        user_message=user_message,
    )

    return {
        "alert_id": alert_id,
        "summary": result["text"],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
    }





@router.get("/{alert_id}/summary/stream")
def stream_alert_summary(alert_id: int):
    context = get_alert_context(alert_id)
    system_prompt = SUMMARY_SYSTEM_PROMPT
    chunks = stream_claude(
        system_prompt=system_prompt,
        user_message=json.dumps(jsonable_encoder(context)),
    )
    # Start the provider request before HTTP headers are sent, so initial errors
    # can still produce their proper HTTP status. Later failures interrupt the stream.
    first = next(chunks, "")

    def body():
        try:
            yield first
            yield from chunks
        finally:
            chunks.close()

    return StreamingResponse(body(), media_type="text/plain")


class TriageResponse(BaseModel):
    decision: Literal["escalate", "recommend_closure", "request_information"]
    likely_typology: str
    reasons: list[str]
    evidence: list[str]
    missing_information: list[str]


@router.post("/{alert_id}/triage", response_model=TriageResponse)
def triage_alert(alert_id: int):
    context = get_alert_context(alert_id)
    system_prompt = (
        "You are an AML investigation assistant. "
        "Recommend exactly one action: escalate, recommend_closure, or request_information. "
        "Return JSON only with these fields: "
        "decision, likely_typology, reasons, evidence, missing_information. "
        "Return exactly one JSON object. "
        "Each field must occur exactly once. "
        "Do not use markdown or code fences. "
        "Use only the supplied evidence. "
        "Do not infer reporting thresholds, transaction timing, "
        "jurisdiction risk, or other facts not explicitly supplied. "
        "Treat unavailable information as missing_information. "
        "You only recommend an action. "
        "Do not change the alert status and do not claim that an alert has been closed."
    )
    result = ask_claude(
        system_prompt=system_prompt,
        user_message=json.dumps(jsonable_encoder(context)),
    )

    print("CLAUDE RAW RESPONSE:", repr(result["text"]))
    raw_text = result["text"].strip()

    try:
        start = raw_text.find("{")
        end = raw_text.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("No JSON object found")

        json_text = raw_text[start:end + 1]

        return TriageResponse.model_validate_json(json_text)

    except ValueError as e:
        print("TRIAGE VALIDATION ERROR:", e)

        raise HTTPException(
            status_code=502,
            detail="Claude returned invalid triage data"
        )




class CreateAlert(BaseModel):
    # Each linked transaction holds its own account_id, allowing multiple accounts.
    transaction_ids: list[int]
    analyst_id: int | None = None
    amount: float = Field(gt=0)
    corridor: str
    rule_triggered: str
    score: float = Field(ge=0, le=1)
    status: Literal["open", "under_review", "closed"] = "open"
    risk_level: Literal["low", "medium", "high"]
    severity: Literal["low", "medium", "high"]


class UpdateAlert(BaseModel):
    transaction_ids: list[int] | None = None
    amount: float | None = Field(default=None, gt=0)
    corridor: str | None = None
    rule_triggered: str | None = None
    score: float | None = Field(default=None, ge=0, le=1)
    status: Literal["open", "under_review", "closed"] | None = None
    risk_level: Literal["low", "medium", "high"] | None = None
    severity: Literal["low", "medium", "high"] | None = None
    analyst_id: int | None = None


class AlertResponse(BaseModel):
    alert_id: int
    transaction_ids: list[int]
    analyst_id: int | None = None
    amount: float
    corridor: str
    rule_triggered: str
    score: float
    status: Literal["open", "under_review", "closed"]
    risk_level: Literal["low", "medium", "high"]
    severity: Literal["low", "medium", "high"]
    created_at: datetime


class CloseAlertRequest(BaseModel):
    reviewer_id: int
    reason: str = Field(min_length=10, max_length=1000)


#List Alerts with filters CRUD

@router.get("/", response_model=list[AlertResponse])
def list_alerts(
    status: str | None = None,
    corridor: str | None = None
):
    results = alerts

    if status:
        results = [a for a in results if a["status"] == status]

    if corridor:
        results = [a for a in results if a["corridor"] == corridor]

    return results


#Get One CRUD

@router.get("/{alert_id}", response_model=AlertResponse)
def get_alert(alert_id: int):
    for alert in alerts:
        if alert["alert_id"] == alert_id:
            return alert

    raise HTTPException(status_code=404, detail="Alert not found")


#CREATE 

@router.post("/", response_model=AlertResponse, status_code=201)
def create_alert(alert: CreateAlert):
    if alert.status == "closed":
        raise HTTPException(
            status_code=403,
            detail=(
                "New alerts cannot be created as closed. "
                "Closure requires an authorised human reviewer."
            ),
        )
    new_id = max((a["alert_id"] for a in alerts), default=0) + 1

    new_alert = {
        "alert_id": new_id,
        **alert.model_dump(),
        "created_at": datetime.now()
    }

    try:
        records = validate_alert_references(new_alert, transactions, accounts, counterparties, rules, analysts)
        if transaction_total(records) != transaction_total([{"amount": new_alert["amount"]}]):
            raise ValueError("Alert amount must equal the total of its linked transactions")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    alerts.append(new_alert)

    return new_alert



#UPDATE
@router.put("/{alert_id}", response_model=AlertResponse)
def update_alert(alert_id: int, update: UpdateAlert):
    for alert in alerts:
        if alert["alert_id"] == alert_id:
            changes = update.model_dump(exclude_unset=True)
            if changes.get("status") == "closed":
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Alert closure requires an authorised human reviewer. "
                        "Use the protected closure workflow."
                    ),
                )
            candidate = {**alert, **changes}
            try:
                # Validate before mutating so failed updates leave the record intact.
                AlertResponse.model_validate(candidate)
                records = validate_alert_references(candidate, transactions, accounts, counterparties, rules, analysts)
                if "transaction_ids" in changes and "amount" not in changes:
                    candidate["amount"] = float(transaction_total(records))
                if transaction_total(records) != transaction_total([{"amount": candidate["amount"]}]):
                    raise ValueError("Alert amount must equal the total of its linked transactions")
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            alert.update(candidate)

            return alert

    raise HTTPException(status_code=404, detail="Alert not found")



@router.post("/{alert_id}/close", response_model=AlertResponse)
def close_alert(
    alert_id: int,
    request: CloseAlertRequest,
    authorised: bool = Depends(verify_reviewer_key),
):
    reviewer = next(
        (
            analyst for analyst in analysts
            if analyst["analyst_id"] == request.reviewer_id
            and analyst.get("status") == "active"
        ),
        None,
    )
    if reviewer is None:
        raise HTTPException(
            status_code=403,
            detail="Reviewer is not an active registered analyst",
        )
    reason = request.reason.strip()
    if len(reason) < 10:
        raise HTTPException(status_code=422, detail="Closure reason must contain at least 10 characters")
    alert = next((a for a in alerts if a["alert_id"] == alert_id), None)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert["status"] == "closed":
        raise HTTPException(status_code=409, detail="Alert is already closed")

    closure_audit.append({
        "alert_id": alert_id,
        "reviewer_id": request.reviewer_id,
        "reason": reason,
        "previous_status": alert["status"],
        "new_status": "closed",
        "closed_at": datetime.now(timezone.utc).isoformat(),
    })
    alert["status"] = "closed"
    return alert


#delete crud

@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int):
    for alert in alerts:
        if alert["alert_id"] == alert_id:
            if any(alert_id in case["alert_ids"] for case in cases):
                raise HTTPException(status_code=409, detail="Cannot delete an alert referenced by a case")
            alerts.remove(alert)
            return

    raise HTTPException(status_code=404, detail="Alert not found")



