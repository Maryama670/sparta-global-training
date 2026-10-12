"""Offline planning estimate; never presented as provider-measured usage."""

import math

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/tokens", tags=["tokens"])


class EstimateRequest(BaseModel):
    text: str = Field(min_length=1, max_length=100000)


@router.post("/estimate")
def estimate_tokens(request: EstimateRequest):
    return {
        "estimated_tokens": math.ceil(len(request.text.encode("utf-8")) / 4),
        "method": "rough UTF-8 byte length divided by four",
        "exact": False,
        "note": "Planning estimate only; excludes system prompts, tools and provider framing.",
    }
