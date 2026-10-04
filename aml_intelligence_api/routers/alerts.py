from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from data import alerts

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"]
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



