import json
import os
from fastapi import APIRouter
from pydantic import BaseModel

from documents import load_documents
from knowledge_store import build_index, search
from llm import ask_claude

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"]
)

RELEVANCE_FLOOR = float(os.getenv("RELEVANCE_FLOOR", "0.35"))


class AskRequest(BaseModel):
    question: str


@router.post("/index")
def index_documents():
    count = build_index()

    return {
        "indexed_documents": count
    }


@router.get("/search")
def search_documents(q: str):
    matches = search(q)

    return {
        "query": q,
        "matches": [
            {
                "id": match["id"],
                "title": match["title"],
                "score": match["score"]
            }
            for match in matches
        ]
    }


@router.post("/ask")
def ask_knowledge(request: AskRequest):
    matches = search(request.question)

    if not matches or matches[0]["score"] < RELEVANCE_FLOOR:
        return {
            "answer": "I do not have sufficient relevant evidence to answer this question.",
            "document_ids": [],
            "input_tokens": 0,
            "output_tokens": 0
        }

    retrieved_documents = "\n\n".join(
        [
            f"DOCUMENT ID: {match['id']}\n{match['text']}"
            for match in matches
        ]
    )

    system_prompt = (
        "You are an AML investigation assistant. "
        "Answer the user's question using only the supplied internal documents. "
        "Do not use outside knowledge. "
        "Do not invent facts. "
        "If the documents do not contain enough evidence, say so."
    )

    user_message = f"""
Question:
{request.question}

Retrieved internal documents:
{retrieved_documents}
"""

    result = ask_claude(
        system_prompt=system_prompt,
        user_message=user_message
    )

    return {
        "answer": result["text"],
        "document_ids": [match["id"] for match in matches],
        "input_tokens": result["input_tokens"],
        "output_tokens": result["output_tokens"]
    }
