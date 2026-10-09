from datetime import datetime
from typing import Literal
import json
import llm 
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from data import accounts, alerts, transactions
from llm import ask_claude, stream_claude


router = APIRouter(
    prefix="/alerts",
    tags=["alerts"]
)


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

    alert_transactions = [
        transaction
        for transaction in transactions
        if transaction["transaction_id"] in alert["transaction_ids"]
    ]

    account_ids = {
        transaction["account_id"]
        for transaction in alert_transactions
    }

    alert_accounts = [
        account
        for account in accounts
        if account["account_id"] in account_ids
    ]

    return {
        "alert": alert,
        "accounts": alert_accounts,
        "transactions": alert_transactions,
    }

@router.post("/{alert_id}/summary")
def summarise_alert(alert_id: int):
    context = get_alert_context(alert_id)

    system_prompt = (
        "You are an AML operations assistant. "
        "Summarise the supplied alert using only the information provided. "
        "Do not invent facts. "
        "Do not decide whether the alert should be closed. "
        "Do not claim that suspicious activity has been proven. "
        "Give a concise factual summary for a human AML analyst."
    )

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
    system_prompt = (
        "You are an AML investigation assistant. "
        "Summarise the supplied alert clearly and concisely. "
        "Use only the supplied evidence. "
        "Do not make a final compliance decision."
    )
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
    decision: Literal["escalate", "close", "request_information"]
    likely_typology: str
    reasons: list[str]
    evidence: list[str]
    missing_information: list[str]


@router.post("/{alert_id}/triage", response_model=TriageResponse)
def triage_alert(alert_id: int):
    context = get_alert_context(alert_id)
    system_prompt = (
        "You are an AML investigation assistant. "
        "Recommend exactly one action: escalate, close, or request_information. "
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

    print(result["text"])
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




    try:
        return TriageResponse.model_validate_json(result["text"])
    except ValueError:
        raise HTTPException(status_code=502, detail="Claude returned invalid triage data")


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
    new_id = max((a["alert_id"] for a in alerts), default=0) + 1

    new_alert = {
        "alert_id": new_id,
        **alert.model_dump(),
        "created_at": datetime.now()
    }

    alerts.append(new_alert)

    return new_alert



#UPDATE
@router.put("/{alert_id}", response_model=AlertResponse)
def update_alert(alert_id: int, update: UpdateAlert):
    for alert in alerts:
        if alert["alert_id"] == alert_id:
            changes = update.model_dump(exclude_unset=True)

            for key, value in changes.items():
                alert[key] = value

            return alert

    raise HTTPException(status_code=404, detail="Alert not found")



#delete crud

@router.delete("/{alert_id}", status_code=204)
def delete_alert(alert_id: int):
    for alert in alerts:
        if alert["alert_id"] == alert_id:
            alerts.remove(alert)
            return

    raise HTTPException(status_code=404, detail="Alert not found")



