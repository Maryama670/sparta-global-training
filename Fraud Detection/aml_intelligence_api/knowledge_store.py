import os

import chromadb
import voyageai
from dotenv import load_dotenv
from fastapi import HTTPException

from documents import load_documents

load_dotenv()

VOYAGE_MODEL = os.getenv("VOYAGE_MODEL", "voyage-3-lite")

voyage_client = (
    voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
    if os.getenv("VOYAGE_API_KEY") else None
)

chroma_client = chromadb.PersistentClient(
    path="./chroma_store"
)

collection = chroma_client.get_or_create_collection(
    name="aml_documents",
    metadata={"hnsw:space": "cosine"}
)

def embed_texts(texts, input_type):
    if voyage_client is None:
        raise HTTPException(status_code=503, detail="Voyage API key is not configured")
    try:
        return voyage_client.embed(texts, model=VOYAGE_MODEL, input_type=input_type)
    except voyageai.error.Timeout as exc:
        raise HTTPException(status_code=504, detail="Voyage request timed out") from exc
    except voyageai.error.RateLimitError as exc:
        raise HTTPException(status_code=429, detail="Voyage rate limit reached") from exc
    except voyageai.error.VoyageError as exc:
        raise HTTPException(status_code=502, detail="Voyage provider error") from exc


def index_is_built():
    return collection.count() > 0


def build_index():
    documents = load_documents()

    texts = [doc["text"] for doc in documents]

    result = embed_texts(texts, input_type="document")

    collection.upsert(
        ids=[doc["id"] for doc in documents],
        embeddings=result.embeddings,
        documents=texts,
        metadatas=[
            {
                "title": doc["title"],
                "type": doc["type"],
                "date": doc["date"],
            }
            for doc in documents
        ],
    )

    return len(documents)

def search(query: str, top_k: int = 3):
    count = collection.count()
    if count == 0:
        return []
    result = embed_texts([query], input_type="query")

    results = collection.query(
        query_embeddings=result.embeddings,
        n_results=min(top_k, count),
    )

    matches = []

    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        score = 1 - distance

        matches.append(
            {
                "id": results["ids"][0][i],
                "title": results["metadatas"][0][i]["title"],
                "text": results["documents"][0][i],
                "score": score,
            }
        )

    return matches
