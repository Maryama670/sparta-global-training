from fastapi import APIRouter, HTTPException  # Import APIRouter to group endpoints and HTTPException to return HTTP errors.
from pydantic import BaseModel, Field  # Import BaseModel for validated data schemas and Field for field constraints and descriptions.
from anthropic import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError  # Import exceptions for provider HTTP errors, request timeouts and rate limits.
import knowledge_store as knowledge  # Load the Chroma-backed storage module under the local name knowledge.
import llm  # Load this project's model helpers and client; access them with the llm. prefix.
import hybrid

# OUR RELEVANCE FLOOR
# BELOW THIS WE TREAT RETREIEVED CONTEXT AS NOT ACTUALLY RLEEVANT
RELEVANCE_FLOOR = 0.35  # Set the minimum similarity score required before using a document.


# create your router
router = APIRouter(prefix="/knowledge", tags=["knowledge"])  # Group these endpoints under the configured URL prefix and documentation tag.


# create your class (QUESTION) using base model
# w. 2 fields (question and top_k)
class Question(BaseModel):  # Define the validated fields for Question.
    question: str = Field(min_length=1)  # Declare question and apply the validation constraints or description shown here.
    top_k: int = Field(default=3, gt=0, le=8)  # Declare top_k and apply the validation constraints or description shown here.


@router.post("/index")  # Register the following function as the handler for this POST route.
def rebuild_index():  # Handle an explicit request to rebuild the document index.
    """Embedding costs tokens, so rebuilding requires a deliberate POST."""
    tokens = knowledge.build_index()  # Rebuild the index and record its embedding token usage.
    return {"indexed": (knowledge.collection.count()), "embedding_tokens": tokens}  # Return {"indexed": len(knowledge.INDEX), "embedding_tokens": tokens} to the caller.


@router.post("/search")  # This carries the data.
def search(q: Question):  # Retrieve the documents most similar to the question.
    """Retrieval only..no model call or generated text etc only what was found !!!"""
    try:  # Attempt the following operations and handle the specified errors below.
        return {  # Build and return a dictionary containing the following fields.
            "question": q.question,  # Include the submitted question in this record.
            "results": knowledge.search(q.question, q.top_k),  # Include results in this record.
        }  # Close the preceding expression or collection.
    except RuntimeError as e:  # Handle RuntimeError and retain it as e.
        raise HTTPException(status_code=409, detail=str(e))  # Stop this request and return HTTP 409 with the supplied error detail.


# function behaviour...
# the refusal happens before the model is called, not after
# why 200 and not a 404 for a refusal???
# the request was valid... service handled it correctly and
# "we have no relevant document" is a real answer
# sources...
# this makes our answer checkable.... without it a client has an answer/para
# that they HAVE to trust.... with it they can open doc-004 and verify the
# claim themselves
# same error mapping as before
# 504, 429, 502.... never a bare 500
@router.post("/ask")  # Register the following function as the handler for this POST route.
def ask(q: Question):  # Retrieve relevant documents and answer from their content, or refuse.
    """retreieve then answer using only what was retieveed or refuse"""
    # 1. Retrieve
    # same call as /knowledge/ search

    try:  # Attempt the following operations and handle the specified errors below.
        hits = knowledge.search(q.question, q.top_k)  # Retrieve the highest-scoring documents for the question.
    except RuntimeError as e:  # Handle RuntimeError and retain it as e.
        raise HTTPException(status_code=409, detail=str(e))  # Stop this request and return HTTP 409 with the supplied error detail.
    usable = [hit for hit in hits if hybrid.is_usable(hit, RELEVANCE_FLOOR)]  # Keep only retrieved documents whose similarity meets the threshold.
    if not usable:  # Take the refusal path when no retrieved document is relevant enough.
        return {  # Build and return a dictionary containing the following fields.
            "question": q.question,  # Include the submitted question in this record.
            "answer": None,  # Include the answer text in this record.
            "reason": "No document in the corpus is relevant to that question",  # Include the explanation for refusing to answer in this record.
            "sources": [],  # Include the supporting document metadata in this record.
        }  # Close the preceding expression or collection.
    # 2.Filter and decide whether to male a call to the model at all
    # (comare against our rleevance_floor)

    # 3. Build context, generate the answer
    context = "\n\n".join(f"[{h['id']}] {h['title']}\n{h['text']}" for h in usable)  # Combine document IDs, titles and text into the context sent to the model.
    try:  # Attempt the following operations and handle the specified errors below.
        result = answer_from_context(q.question, context)  # Generate an answer using the question and retrieved context.
    except APITimeoutError:  # Handle APITimeoutError.
        raise HTTPException(status_code=504, detail="Answer provider timed out")  # Stop this request and return HTTP 504 with the supplied error detail.
    except RateLimitError:  # Handle RateLimitError.
        raise HTTPException(status_code=429, detail="Answer provider rate limited")  # Stop this request and return HTTP 429 with the supplied error detail.
    except (APIStatusError, APIConnectionError):  # Handle APIStatusError.
        raise HTTPException(status_code=502, detail="Answer provider unavailable")  # Stop this request and return HTTP 502 with the supplied error detail.


    return {
        "question": q.question,
        "answer": result["answer"],
        "refused": False,
        "sources": [{"id":hit["id"], "title":hit["title"], "score":hit["score"]} for hit in usable],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"],
        "stop_reason": result["stop_reason"],
        "grounding": grounding.check_citations(result["answer"], [h["id"] for h in usable])
    }