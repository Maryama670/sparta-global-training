"""Translate upstream failures without returning provider bodies or secrets."""
from contextlib import contextmanager

import anthropic
import voyageai
from fastapi import HTTPException


@contextmanager
def mapped_provider_errors():
    try:
        yield
    except (anthropic.APITimeoutError, voyageai.error.Timeout) as exc:
        raise HTTPException(status_code=504, detail="AI provider timed out") from exc
    except (anthropic.RateLimitError, voyageai.error.RateLimitError) as exc:
        raise HTTPException(status_code=429, detail="AI provider rate limited") from exc
    except (anthropic.APIError, voyageai.error.VoyageError) as exc:
        raise HTTPException(status_code=502, detail="AI provider unavailable") from exc
