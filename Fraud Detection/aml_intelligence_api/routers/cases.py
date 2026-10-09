from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


class Case(BaseModel):
    """An investigation grouping one or more alerts for human review."""

    case_id: int = Field(gt=0)
    # These IDs link to Alert; account and rule details come from those alerts.
    alert_ids: list[Annotated[int, Field(gt=0)]] = Field(min_length=1)
    analyst_id: int = Field(gt=0)
    status: str = Field(min_length=1)
    priority: str = Field(min_length=1)
    opened_at: datetime
    closed_at: datetime | None = None
    outcome: str | None = None
    notes: str = ""
