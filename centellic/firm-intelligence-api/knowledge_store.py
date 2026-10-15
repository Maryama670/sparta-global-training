# embed_texts.... is imported, not rewritten
# embedding provider has not changed.... only where the vectors get stored

import knowledge
import chunk_index
import hybrid

# our chosen strategy 
CHUNK_STRATEGY = "sections_contextual"

SEARCH_MODE = "hybrid"  

# chroma = chromadb.PersistentClient(path="./chroma_store")
# collection = chroma.get_or_create_collection(
#     name = "firm_documents",
#     # HNSW (hierachchial Navigable Small World) is a graph 
#     # based index used in vector databased to perform fast and 
#     # appropriate nearest neighbour search in high dimensional data
#     configuration={"hnsw": {"space": "cosine"}},
# )

def count() -> int:
    return chunk_index.collection_for(CHUNK_STRATEGY).count()

def build_index() -> int:
    """Chunk and embed the corpus... Free is nothing has changed since the last build."""
    return chunk_index.build(CHUNK_STRATEGY)["embedding_tokens"]

# Chroma will give us back distance... lower is closer...
def search(question: str, top_k: int = 3) -> list[dict]:
    """embed the question and let chroma do the storing."""
    if count() == 0:
        raise RuntimeError("Index is empty, call POST /knowledge/ask/index first")
    query_vectors, _ = knowledge.embed_texts([question], input_type="query")
    if SEARCH_MODE == "hybrid":
        return hybrid.search_with_vector(CHUNK_STRATEGY, question, query_vectors[0], top_k)
    return chunk_index.search_with_vectors(CHUNK_STRATEGY, query_vectors, k=top_k)