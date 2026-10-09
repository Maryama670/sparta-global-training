from pydantic import BaseModel, Field


class Analyst(BaseModel):
    """An AML analyst responsible for reviewing investigations."""

    analyst_id: int = Field(gt=0)
    name: str = Field(min_length=1)
    team: str = Field(min_length=1)
    role: str = Field(min_length=1)
    experience_level: str = Field(min_length=1)
    # A count of active cases, rather than a list of case IDs.
    active_cases: int = Field(default=0, ge=0)
    status: str = Field(min_length=1)
