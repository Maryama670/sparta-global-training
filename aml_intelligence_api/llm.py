import os

import anthropic
from dotenv import load_dotenv
from fastapi import HTTPException


load_dotenv()

MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
TIMEOUT = float(os.environ.get("CLAUDE_TIMEOUT", "30"))

client = (
    anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        timeout=TIMEOUT,
        max_retries=0,
    )
    if os.environ.get("ANTHROPIC_API_KEY")
    else None
)


def get_client():
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Claude API key is not configured",
        )
    return client


def ask_claude(system_prompt: str, user_message: str):
    try:
        response = get_client().messages.create(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        )

        return {
            "text": "".join(
                block.text
                for block in response.content
                if block.type == "text"
            ),
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

    except anthropic.APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Claude request timed out",
        )

    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Claude rate limit reached",
        )

    except anthropic.APIError:
        raise HTTPException(
            status_code=502,
            detail="Claude provider error",
        )


def stream_claude(system_prompt: str, user_message: str):
    try:
        with get_client().messages.stream(
            model=MODEL,
            max_tokens=500,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_message,
                }
            ],
        ) as stream:
            for text in stream.text_stream:
                yield text

    except anthropic.APITimeoutError:
        raise HTTPException(
            status_code=504,
            detail="Claude request timed out",
        )

    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Claude rate limit reached",
        )

    except anthropic.APIError:
        raise HTTPException(
            status_code=502,
            detail="Claude provider error",
        )