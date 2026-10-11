from decimal import Decimal

from pydantic import BaseModel, Field


class Rule(BaseModel):
    """An AML detection rule, such as structuring or high_value_transfer."""

    rule_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    # The rule's description should explain the threshold's units and meaning.
    # Qualitative detection rules need no invented numeric/legal threshold.
    threshold: Decimal | None = Field(default=None, ge=0)
    guidance_doc_id: str = Field(pattern=r"^doc-\d{3}$")
    severity: str = Field(min_length=1)
    active: bool
