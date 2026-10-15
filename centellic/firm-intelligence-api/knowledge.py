"""Embedding adnn retrevel mechanics...nothing in here will know about ?api?"""

import math  # Load maths helpers, including the square root used to calculate vector lengths.
import os  # Load operating-system helpers so API keys can be read from environment variables.
import voyageai  # Load the Voyage SDK used to turn text into embedding vectors.

from documents import DOCUMENTS  # Import the sample document list used to build the search index.

EMBEDED_MODEL = "voyage-3-lite"  # Choose the Voyage model that converts text into vectors.


voyage = voyageai.Client(  # Create the Voyage embedding client with the settings below.
    api_key=os.environ["VOYAGE_API_KEY"],  # Read the provider API key from the environment.
    max_retries=3,  # Set how many times the SDK may retry a failed request.
    timeout=60,  # Set the provider request timeout in seconds.
)  # Close the preceding expression or collection.

#the inmemory a list of dicts exactly like firms last week

INDEX: list[dict] = []  # Keep document records and their vectors in a list in memory.



def embed_text(texts: list[str], input_type: str) -> tuple[list[list[float]], int]:  # Convert a batch of text strings into vectors and return token usage.
    # Embed a batch.
    # input_type tells Voyage whether these are documents or a query.this only part that speaks to voy
    result = voyage.embed(  # Send the text batch to Voyage and retain the embedding response.
        texts=texts,  # Supply the batch of text strings to embed.
        model=EMBEDED_MODEL,  # Choose the model used for this request.
        input_type=input_type,  # Tell the embedding model whether this text is a document or a query.
    )  # Close the preceding expression or collection.

    # Return the vectors and token count (to track cost).
    return result.embeddings, result.total_tokens  # Return the embedding vectors and the number of tokens used.


def cosine_similarity(a: list[float], b: list[float]) -> float:  # Calculate how closely two vectors point in the same direction.
    """how close are two vectors in direction, ignoring their length 1.0 means identical direction
    1.0 means dientical direction
    0.0 means unrelated
    -1.0 means opposite"""

    if not a or len(a) != len(b):
        raise ValueError("Vectors must be non-empty and have matching dimensions")
    dot = sum(x * y for x, y in zip(a,b))  # Multiply matching vector coordinates and add them to get the dot product.
    norm_a = math.sqrt(sum(x * x for x in a))  # Calculate the length of the first vector.
    norm_b = math.sqrt(sum(y * y for y in b))  # Calculate the length of the second vector.
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b )  # Divide by both vector lengths to obtain cosine similarity.


def build_index() -> int:  # Rebuild the in-memory document search index.
    """Embed every document once and hold the vectors in memory"""
    texts = [doc ["body"] for doc in DOCUMENTS]  # Extract the body text from each document for embedding.

    vectors,tokens = embed_text(texts,input_type = "document")  # Embed every document and retain the total token usage.
    if len(vectors) != len(DOCUMENTS):
        raise RuntimeError("Embedding count does not match document count")
    INDEX.clear()  # Replace the index only after embedding succeeds.
    for doc , vector in zip(DOCUMENTS, vectors):  # Pair each source document with its corresponding embedding.
        INDEX .append({  # Add a document record and its vector to the in-memory index.
        "id": doc["id"],  # Include the record identifier in this record.
        "title": doc["title"],  # Include the document title in this record.
        "text": doc["body"],  # Include the document text in this record.
        "vector": vector  # Include the embedding vector in this record.

        })  # Close the preceding expression or collection.

    return tokens  # Return tokens to the caller.

def search(question:str, top_k:int = 3) -> list[dict]:  # Retrieve the documents most similar to the question.
    """Embed the question ..then score it against everything in the index"""
    if not INDEX:  # Check whether the document index is empty.
        raise RuntimeError("Index is empty - call build_index() first")  # Stop the search because the index has not been built.
    query_vectors, _ = embed_text([question], input_type="query")  # Embed the question as a query and discard the token count.
    query_vector = query_vectors[0]  # Extract the single question vector from the returned batch.

    scored = [  # Build the list of documents and their similarity scores.
        { "id": entry["id"],  # Start a search result with the indexed document identifier.
         "title": entry["title"],  # Include the document title in this record.
         "text": entry["text"],  # Include the document text in this record.
         "score": cosine_similarity(query_vector, entry["vector"])  # Include the similarity score in this record.
        }  # Close the preceding expression or collection.
        for entry in INDEX  # Build one scored result for each indexed document.
    ]  # Close the preceding expression or collection.

    scored.sort(key=lambda item: item["score"], reverse=True)  # Sort documents from highest to lowest similarity score.
    return scored[:top_k]  # Return at most the requested number of highest-scoring documents.


