from anthropic import APIStatusError, APITimeoutError, RateLimitError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# import knowledge
import knowledge_store as knowledge
import grounding
import llm

# our relevance floor
# Below this we treat the retrieved context as not actually relevant
from configuration import RELEVANCE_FLOOR
from context import build_context
from provider_errors import mapped_provider_errors

router = APIRouter(prefix="/knowledge",tags=["knowledge"])

class Question(BaseModel):
    question : str = Field(min_length=3)
    top_k : int = Field(default=3, gt=0, le=8)

# POST does something, GET only retrieves. Here POST builds the index and sends real tokens with a cost.
# POST because it acts
@router.post("/index")
def rebuild_index():
    """Embed the corpus. Costs tokens... so it is a deliberate POST, rather than automatic"""
    with mapped_provider_errors():
        tokens = knowledge.build_index()
    return {"indexed" : knowledge.count(), "embedding_tokens" : tokens}

# POST because it needs to carry data in a response body. GET requests are not meant to take a request body by convention.
@router.post("/search")
def get_docs(question : Question):
    """Retrieval only... no model call or generated text etc... only what was found"""
    try:
        with mapped_provider_errors():
            results = knowledge.search(question.question, question.top_k)
        return {
            "question" : question.question,
            "results" : results
        }
    except RuntimeError as e:
        raise HTTPException(status_code= 409, detail = str(e))

@router.post("/ask")
def ask(q : Question):

    """Retrieve, then answer using only what was retrieved... or refuse"""
    # 1. Retrieve
    # same call as /knowledge/search
    try:
        with mapped_provider_errors():
            hits = knowledge.search(q.question, q.top_k)

    except RuntimeError as e:
        raise HTTPException(status_code= 409, detail = str(e))


    # 2. Filter, and decide whether to make a call to the model at all.
    # compare against our RELEVANCE_FLOOR
    usable = [hit for hit in hits if hit["score"] >= RELEVANCE_FLOOR]

    if not usable:
        return {
            "question" : q.question,
            "answer" : None,
            "refused" : True,
            "reason" : "No document in the corpus is relevant to that question.",
            "sources" : []
        }

    # 3. Generation, Build context and generate the answer
    context = build_context(usable)
    try:
        with mapped_provider_errors():
            result = llm.answer_from_context(q.question, context)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail="Answer provider unavailable") from exc

    report = grounding.check_citations(result["answer"], [h["id"] for h in usable])
    refused = report["refusal"] or not report["passed"]

    return {
        "question" : q.question,
        "answer" : None if refused else result["answer"],
        "refused" : refused,
        "sources": [] if refused else [{"id" : h["id"],"title" : h["title"],"score" : round(h["score"],3)} for h in usable],
        "input_tokens" : result["input_tokens"],
        "output_tokens" : result["output_tokens"],
        "stop_reason" : result["stop_reason"],
        "grounding" : report
    }
