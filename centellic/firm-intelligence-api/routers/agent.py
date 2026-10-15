from anthropic import APIStatusError, APITimeoutError, RateLimitError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from agent import ask_with_tools


router = APIRouter(prefix="/agent", tags=["agent"])

class AgentQuestion(BaseModel):
     question: str = Field(min_length=3)

class ToolUseResponse(BaseModel):
    answer: str
    complete: bool
    tool_calls_made: int
    input_tokens: int
    output_tokens: int
    stop_reason: str

@router.post("/ask")
def ask_agent_with_tools(query:AgentQuestion) -> ToolUseResponse:
    try:
        result = ask_with_tools(query.question)
        return result
    except RateLimitError:
            raise HTTPException(status_code=429, detail="LLM rate limit exceeded")
    except APITimeoutError:
        raise HTTPException(status_code=504, detail="LLM request timed out")
    except APIStatusError:
        raise HTTPException(status_code=502, detail="Failed to generate the response")