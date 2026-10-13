#embed texts .... is imported, not rewritten
#the embedding provider has not changed... only where the vectors get stored


import knowledge
import chunk_index


#our chosen strategy
CHUNK_STRATEGY = "section_contextual"

def count() -> int:
    return chunk_index.collection_for(CHUNK_STRATEGY).count()

def build_index() -> int:
    """Chunk and embed the corpus.. free if nothing has changed since the last build."""
    return chunk_index.build(CHUNK_STRATEGY)["embedding_tokens"]


def search(question: str, top_k: int = 3) -> list[dict]:
    """Embed the question and let chroma do the storage."""
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    if count() == 0:
        raise RuntimeError("Index is empty, call POST /knowledge/index first")
    query_vectors, _ = knowledge.embed_text([question], input_type="query")

    return chunk_index.search_with_vectors(CHUNK_STRATEGY, query_vectors, k=top_k)[0]
