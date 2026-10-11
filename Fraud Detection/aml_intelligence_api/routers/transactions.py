from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """A movement of money between an account and a counterparty."""

    transaction_id: int = Field(gt=0)
    account_id: int = Field(gt=0)  # Links to Account.
    counterparty_id: int = Field(gt=0)  # Links to Counterparty.
    amount: Decimal = Field(gt=0)  # Decimal avoids binary float rounding for money.
    # Existing records intentionally leave these facts unknown. Never derive a
    # payment timestamp from an alert's creation date or assume a currency.
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    corridor: str | None = Field(default=None, min_length=1)
    transaction_type: str | None = Field(default=None, min_length=1)
    timestamp: datetime | None = None
