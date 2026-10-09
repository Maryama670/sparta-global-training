from pydantic import BaseModel, Field


class Counterparty(BaseModel):
    """The other person, company or account involved in a transaction."""

    counterparty_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    country: str = Field(min_length=1)
    # Text preserves leading zeros and allows synthetic alphanumeric identifiers.
    account_identifier: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    risk_level: str = Field(min_length=1)
    sanctions_flag: bool
