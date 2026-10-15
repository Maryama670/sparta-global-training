from anthropic import APIStatusError, APITimeoutError, RateLimitError
from fastapi import APIRouter, HTTPException, Depends
from pydantic import ValidationError
from fastapi.responses import StreamingResponse
import llm
from routers.firms import get_firm_or_404

router = APIRouter(prefix="/firms", tags=["insights"])


@router.post("/{firm_id}/summary")
def create_insights(firm: dict = Depends(get_firm_or_404)):
    try:
        return llm.summarise_firm(firm)
    except RateLimitError:
        raise HTTPException(status_code=429, detail="LLM rate limit exceeded")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")
    except APIStatusError:
        raise HTTPException(status_code=502, detail="Failed to generate firm summary")

@router.post("/{firm_id}/structured_analysis")
def create_structured_analysis(firm:dict = Depends(get_firm_or_404)):
    try:
        return llm.analyse_frim(firm)
    except RateLimitError:
        raise HTTPException(status_code=429, detail="LLM rate limit exceeded")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")
    except APIStatusError:
        raise HTTPException(status_code=502, detail="Failed to generate firm summary")
    except ValidationError:
        raise HTTPException(
            status_code=502,
            detail="LLM returned invalid structured output"
        )

@router.get("/{firm_id}/summary/estimate")
def estimate(firm_id, firm:dict = Depends(get_firm_or_404)):
    return{
        "id":firm["id"],
        "estimated_input_tokens": llm.estimate_input_tokens(firm),
        "model": llm.MODEL
    }

@router.get("/{firm_id}/summary/stream")
def stream_summary(firm: dict = Depends(get_firm_or_404)):
    return StreamingResponse(
        llm.stream_firm_summary(firm),
        media_type="text/plain", )