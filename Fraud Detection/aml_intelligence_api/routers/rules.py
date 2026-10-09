from decimal import Decimal

from pydantic import BaseModel, Field


class Rule(BaseModel):
    """An AML detection rule, such as structuring or high_value_transfer."""

    rule_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    # The rule's description should explain the threshold's units and meaning.
    threshold: Decimal = Field(ge=0)
    severity: str = Field(min_length=1)
    active: bool
