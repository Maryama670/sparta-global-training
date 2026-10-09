from fastapi import APIRouter
from pydantic import BaseModel

from agent import ask_with_tools


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


class AgentRequest(BaseModel):
    question: str
    alert_id: int | None = None


@router.post("/ask")
def ask_agent(request: AgentRequest):
    question = request.question

    if request.alert_id is not None:
        question = f"For alert {request.alert_id}: {question}"

    return ask_with_tools(question)