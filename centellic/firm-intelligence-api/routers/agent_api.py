import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from routers import agent

router = APIRouter(prefix="/agent", tags=["agent"])


class AgentAskRequest(BaseModel):
    question: str = Field(min_length=1)


@router.post("/ask")
def ask_agent(request: AgentAskRequest):
    try:
        return agent.ask_with_tools(request.question)

    except anthropic.APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="AI provider timed out",
        )

    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="AI provider rate limit exceeded",
        )

    except anthropic.APIConnectionError:
        raise HTTPException(
            status_code=502,
            detail="AI provider unavailable",
        )

    except anthropic.APIError:
        raise HTTPException(
            status_code=502,
            detail="AI provider error",
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Agent request failed",
        )
