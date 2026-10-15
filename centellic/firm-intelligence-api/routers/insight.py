from anthropic import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError  # Import exceptions for provider HTTP errors, request timeouts and rate limits.
from fastapi import APIRouter, Depends, HTTPException  # Import APIRouter to group routes, Depends to resolve dependencies and HTTPException to return errors.
from fastapi.responses import StreamingResponse  # Import the response class that sends generated text to the caller in chunks.

import llm  # Load this project's model helpers and client; access them with the llm. prefix.
from routers.firms import get_firm_or_404  # Import the helper that finds a firm by ID or raises an HTTP 404 error.


router = APIRouter(prefix="/firms", tags=["insights"])  # Group these endpoints under the configured URL prefix and documentation tag.


@router.post("/{firm_id}/summary")  # Register the following function as the handler for this POST route.
def summarise(firm: dict = Depends(get_firm_or_404)):  # Serve a generated summary and translate provider errors into HTTP errors.
    try:  # Attempt the following operations and handle the specified errors below.
        return llm.summarise_firm(firm)  # Return llm.summarise_firm(firm) to the caller.
    except APITimeoutError:  # Handle APITimeoutError.
        raise HTTPException(status_code=504, detail="Summary provider timed out")  # Stop this request and return HTTP 504 with the supplied error detail.
    except RateLimitError:  # Handle RateLimitError.
        raise HTTPException(status_code=429, detail="Summary provider rate limited")  # Stop this request and return HTTP 429 with the supplied error detail.
    except (APIStatusError, APIConnectionError):  # Handle APIStatusError.
        raise HTTPException(status_code=502, detail="Summary provider unavailable")  # Stop this request and return HTTP 502 with the supplied error detail.


@router.get("/{firm_id}/summary/estimate")  # Register the following function as the handler for this GET route.
def estimate(firm: dict = Depends(get_firm_or_404)):  # Serve a token estimate for a firm summary.
    try:  # Attempt the following operations and handle the specified errors below.
        return {"id": firm["id"], "estimated_input_tokens": llm.estimate_input_tokens(firm)}  # Return the estimated input usage before generation.
    except APITimeoutError:  # Handle APITimeoutError.
        raise HTTPException(status_code=504, detail="Summary provider timed out")  # Stop this request and return HTTP 504 with the supplied error detail.
    except RateLimitError:  # Handle RateLimitError.
        raise HTTPException(status_code=429, detail="Summary provider rate limited")  # Stop this request and return HTTP 429 with the supplied error detail.
    except (APIStatusError, APIConnectionError):  # Handle APIStatusError.
        raise HTTPException(status_code=502, detail="Summary provider unavailable")  # Stop this request and return HTTP 502 with the supplied error detail.


@router.get("/{firm_id}/summary/stream")  # Register the following function as the handler for this GET route.
def stream_summary(firm: dict = Depends(get_firm_or_404)):  # Serve a firm summary as a streaming response.
    return StreamingResponse(  # Return an HTTP response that sends text as chunks become available.
        llm.stream_firm_summary(firm),  # Supply the generator that produces summary chunks.
        media_type="text/plain",  # Tell the client that the streamed response contains plain text.
    )  # Close the preceding expression or collection.


#endpoint challenge 
#POST endpoint at firms/firm_id/analysis
#tries to analyse firm...if not,raises appropriate exception(s)

@router.post("/{firm_id}/analysis")  # Register the following function as the handler for this POST route.
def firm_analysis(firm: dict = Depends(get_firm_or_404)):  # Serve a structured firm analysis and translate provider errors.
    try:  # Attempt the following operations and handle the specified errors below.
        return llm.analyse_firm(firm)  # Return llm.analyse_firm(firm) to the caller.
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    except APITimeoutError:  # Handle APITimeoutError.
        raise HTTPException(status_code=504, detail="Analysis provider timed out")  # Stop this request and return HTTP 504 with the supplied error detail.
    except RateLimitError:  # Handle RateLimitError.
        raise HTTPException(status_code=429, detail="Analysis provider rate limited")  # Stop this request and return HTTP 429 with the supplied error detail.
    except (APIStatusError, APIConnectionError):  # Handle APIStatusError.
        raise HTTPException(status_code=502, detail="Analysis provider unavailable")  # Stop this request and return HTTP 502 with the supplied error detail.
