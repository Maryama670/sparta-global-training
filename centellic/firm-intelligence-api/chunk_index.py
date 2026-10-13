"""
corpus.py and documents.py compare startegies we need a vector index
one chroma collection per chunking stategy so tha the startgeies can be compared side by side

each collection rememebrs a fingeeprint of the chunks and embedding model that built
if either chanes the collection is rebuilt from scratch

"""
# embed_texts is imported not rewritten... embedding provider hasn't changed... only the storage has
# configuration=.... -> not optional, we are choosing something different from Chromas default
# Chroma retuirn distance, we return similarity
    # in Chroma, lower is better
    # higher was better for ours.... (1 - distance) converts
# upsert instead of add -> add fails on an id that already exists, upsert overwrites

import hashlib
import chromadb
import chunking
import knowledge
from corpus import CORPUS_DOCUMENTS
from documents import DOCUMENTS


ALL_DOCUMENTS = DOCUMENTS + CORPUS_DOCUMENTS


BATCH_SIZE = 128 #Voyage's own guidance: batch documents to stay well inside rate limits


chroma = chromadb.PersistentClient(path="./chroma_store")
def collection_name(strategy: str) -> str:
    return f"chunks_{strategy}"

def collection_for(strategy: str):
    return chroma.get_or_create_collection(
        name=collection_name(strategy), configuration={"hnsw": {"space": "cosine"}}

    )
def embed_batched(texts: list[str], input_type: str) -> tuple[list[list[float]], int]:
    """embed any number of texts in batches. Return all vectors and totoal token count"""

    vectors: list[list[float]] = []
    tokens = 0
    for start in range(0, len(texts), BATCH_SIZE):
        batch_vectors, batch_tokens = knowledge.embed_text(texts[start : start + BATCH_SIZE], input_type=input_type)
        vectors.extend(batch_vectors)
        tokens += batch_tokens
    return vectors, tokens

# if the fingerptin changes if the text, the model or the order changes...and stays put of nothing does
def fingerprint(chunks: list[dict]) -> str:
    # SHA 256- a recipe that truns any text into a  fixed-length code (64 chars)
    digest = hashlib.sha256(knowledge.EMBED_MODEL.encode())
    for c in chunks:
        digest.update(f"{c['id']}\n{c['text']}\n".encode())
    return digest.hexdigest()[:16]

def build(strategy: str, force: bool = False) -> dict:
    """Make sure the startegy's collection matches the current corpus, chunker model"""
    """ Answers one q... is the index I already have still correct?"""

    chunks = chunking.chunk_corpus(ALL_DOCUMENTS, strategy)
    fp = fingerprint(chunks)
    col = collection_for(strategy)
    stored = col.get(limit=1, include=["metadatas"])["metadatas"]


    if not force and col.count() == len(chunks) and stored and stored[0].get("fingerprint") == fp:
        return {"strategy": strategy, "chunks": len(chunks), "embedding_tokens": 0, "rebuilt": False}
    # pt2 - the rebuild
    try:
        chroma.delete_collection(collection_name(strategy))
    except Exception:
        pass

    col = collection_for(strategy)
    vectors, tokens = embed_batched([c["text"] for c in chunks], input_type="document")
    col.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=vectors,
        documents=[c["text"] for c in chunks],
        metadatas=[{"doc_id": c["doc_id"], "title": c["title"], "fingerprint": fp}
            for c in chunks],
    )

    return {"strategy": strategy, "chunks": len(chunks), "embedding_tokens": tokens, "rebuilt": True}

# CURRENT -


# nEW FUNCTIONS ADDS - search_with_vectors
# the read side
# it takes question vectors that are already embedded, so questions are embedded once and re-used across all six categories


def search_with_vectors(strategy: str, query_vectors: list[list[float]], k: int) -> list[list[dict]]:
    """
    we embed the question once, then searches many stratgeies with the same vectors
      """
    if type(k) is not int or k < 1:
        raise ValueError("k must be a positive integer")
    col = collection_for(strategy)
    if col.count() == 0:
        raise RuntimeError(f"Index for '{strategy}' is emoty, build it first")

    # the search
    result = col.query(query_embeddings=query_vectors, n_results=min(k, col.count()))
    # what results looks like
    # what result looks like
    # - result["ids"] - a list of 2 lists, each holding 3 ids
    # - result["documents"] - a list of 2 lists, each holding 3 texts
    # - result["metadatas"] - a list of 2 lists, each holding 3 metadata dictionaires
    # - result["diatances"] - a list of 2 lists, each holding 3 distances
    # e.g. ids            ['doc-001#00', 'doc-101#01', 'doc-107#00']
    # e.g. distances      [0.375, 0.389, 0.30]

    return [
        [
            {
                "id": meta["doc_id"],
                "chunk_id": chunk_id,
                "title": meta["title"],
                "text": text,
                "score": 1 - distance,
            }
            for chunk_id, text, meta, distance in zip(ids, docs, metas, dists)
        ]
        for ids, docs, metas, dists in zip(
            result["ids"],
            result["documents"],
            result["metadatas"],
            result["distances"],
        )
    ]
