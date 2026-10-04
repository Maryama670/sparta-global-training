from data import accounts, alerts, transactions, counterparties
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/accounts",
    tags=["accounts"]
)

class CreateAccount(BaseModel):
    customer_name: str = Field(min_length=1)
    country: str = Field(min_length=1)
    occupation: str = Field(min_length=1)
    expected_monthly_activity: float = Field(gt=0)
    source_of_funds: str = Field(min_length=1)
    risk_level: Literal["low", "medium", "high"]


class UpdateAccount(BaseModel):
    customer_name: str | None = None
    country: str | None = None
    occupation: str | None = None
    expected_monthly_activity: float | None = Field(default=None, gt=0)
    source_of_funds: str | None = None
    risk_level: Literal["low", "medium", "high"] | None = None


class AccountResponse(BaseModel):
    account_id: int
    customer_name: str
    country: str
    occupation: str
    expected_monthly_activity: float
    source_of_funds: str
    risk_level: Literal["low", "medium", "high"]



@router.get("/{account_id}/alerts")
def get_account_alerts(account_id: int):
    account_exists = any(
        account["account_id"] == account_id
        for account in accounts
    )

    if not account_exists:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    account_transaction_ids = {
        transaction["transaction_id"]
        for transaction in transactions
        if transaction["account_id"] == account_id
    }

    return [
        alert
        for alert in alerts
        if account_transaction_ids.intersection(alert["transaction_ids"])
    ]



@router.get("/{account_id}/transactions")
def get_account_transactions(account_id: int):
    account_exists = any(
        account["account_id"] == account_id
        for account in accounts
    )

    if not account_exists:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    return [
        transaction
        for transaction in transactions
        if transaction["account_id"] == account_id
    ]