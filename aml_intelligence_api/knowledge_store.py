import os

import chromadb
import voyageai
from dotenv import load_dotenv

from documents import load_documents

load_dotenv()

VOYAGE_MODEL = "voyage-3-lite"

voyage_client = voyageai.Client(
    api_key=os.environ["VOYAGE_API_KEY"]
)

chroma_client = chromadb.PersistentClient(
    path="./chroma_store"
)

collection = chroma_client.get_or_create_collection(
    name="aml_documents",
    metadata={"hnsw:space": "cosine"}
)

def build_index():
    documents = load_documents()

    texts = [doc["text"] for doc in documents]

    result = voyage_client.embed(
        texts,
        model=VOYAGE_MODEL,
        input_type="document"
    )

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
    result = voyage_client.embed(
        [query],
        model=VOYAGE_MODEL,
        input_type="query"
    )

    results = collection.query(
        query_embeddings=result.embeddings,
        n_results=top_k,
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