import os

import anthropic
from dotenv import load_dotenv
from fastapi import HTTPException


load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
TIMEOUT = float(os.environ.get("CLAUDE_TIMEOUT", "30"))

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    timeout=TIMEOUT,
    max_retries=0,
) if os.environ.get("ANTHROPIC_API_KEY") else None


def get_client():
    if client is None:
        raise HTTPException(status_code=503, detail="Claude API key is not configured")
    return client


# Temporary development mocks: no Claude requests are made.
def ask_claude(system_prompt: str, user_message: str):
    if "Recommend exactly one action" in system_prompt:
        return {
            "text": """
            {
                "decision": "escalate",
                "likely_typology": "structuring",
                "reasons": ["Multiple linked transactions"],
                "evidence": ["Transactions 101, 102 and 103"],
                "missing_information": ["Purpose of payments"]
            }
            """,
            "input_tokens": 100,
            "output_tokens": 25,
        }
    return {
        "text": "This alert shows several linked transactions consistent with possible structuring activity and warrants further review.",
        "input_tokens": 100,
        "output_tokens": 25,
    }


def stream_claude(system_prompt: str, user_message: str):
    words = ["Mock ", "streaming ", "AML ", "summary."]
    for word in words:
        yield word
