from data import accounts, alerts, transactions, counterparties
from typing import Literal
from pydantic import BaseModel, Field, model_validator
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
    customer_name: str | None = Field(default=None, min_length=1)
    country: str | None = Field(default=None, min_length=1)
    occupation: str | None = Field(default=None, min_length=1)
    expected_monthly_activity: float | None = Field(default=None, gt=0)
    source_of_funds: str | None = Field(default=None, min_length=1)
    risk_level: Literal["low", "medium", "high"] | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_values(cls, data):
        if isinstance(data, dict):
            for field, value in data.items():
                if value is None:
                    raise ValueError(
                        f"{field} cannot be null"
                    )
        return data

class AccountResponse(BaseModel):
    account_id: int
    customer_name: str
    country: str
    occupation: str
    expected_monthly_activity: float
    source_of_funds: str
    risk_level: Literal["low", "medium", "high"]

@router.get("/", response_model=list[AccountResponse])
def list_accounts(
    country: str | None = None,
    risk_level: Literal["low", "medium", "high"] | None = None,
):
    results = accounts

    if country is not None:
        results = [
            account for account in results
            if account["country"] == country
        ]

    if risk_level is not None:
        results = [
            account for account in results
            if account["risk_level"] == risk_level
        ]

    return results
@router.post("/", response_model=AccountResponse, status_code=201)
def create_account(account: CreateAccount):
    new_account = account.model_dump()

    new_account["account_id"] = max(
        (a["account_id"] for a in accounts),
        default=0
    ) + 1

    accounts.append(new_account)

    return new_account

@router.get("/{account_id}", response_model=AccountResponse)
def get_account(account_id: int):
    account = next(
        (a for a in accounts if a["account_id"] == account_id),
        None
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    return account
@router.put("/{account_id}", response_model=AccountResponse)
def update_account(account_id: int, updated_account: UpdateAccount):
    account = next(
        (a for a in accounts if a["account_id"] == account_id),
        None
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    changes = updated_account.model_dump(exclude_unset=True)

    account.update(changes)

    return account
@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int):
    account = next(
        (a for a in accounts if a["account_id"] == account_id),
        None
    )

    if account is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    has_transactions = any(
        transaction["account_id"] == account_id
        for transaction in transactions
    )

    if has_transactions:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete an account with transaction history"
        )

    accounts.remove(account)
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