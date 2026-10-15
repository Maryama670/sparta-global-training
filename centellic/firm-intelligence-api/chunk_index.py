"""
One chroma collection per chunking strategy. so that strategies can be compaired side by side
If either changes , the collection will be rebuilt from the scratch.

WRITE (run once, free if nothing changed)
chunking.py  ->  chunk_corpus  ->  build  ->  embed_batched  ->  Voyage  ->  Chroma "chunks_<strategy>"


READ (run for every question)
question vector  ->  search_with_vectors  ->  Chroma "chunks_<strategy>"  ->  ranked hits

"""

import chromadb
import hashlib
import chunking
import knowledge
from corpus import CORPUS_DOCUMENTS
from documents import DOCUMENTS

ALL_DOCUMENTS = DOCUMENTS + CORPUS_DOCUMENTS

BATCH_SIZE = (
    128  # Voyage's own guidance : bactch documents to stay well inside rate limits
)

chroma = chromadb.PersistentClient(path="./chroma_store")


def collection_name(startegy: str) -> str:
    return f"chunk_{startegy}"


def collection_for(startegy: str):
    return chroma.get_or_create_collection(
        name=collection_name(startegy), configuration={"hnsw": {"space": "cosine"}}
    )


def embed_batched(texts: list[str], input_type: str) -> tuple[list[list[float]], int]:
    """
    embed every number of texts in batches, return all vectors and total token count .
    """
    vectors: list[list[float]] = []
    tokens = 0

    for start in range(0, len(texts), BATCH_SIZE):
        batch_vectors, batch_tokens = knowledge.embed_texts(
            texts[start : start + BATCH_SIZE], input_type=input_type
        )
        vectors.extend(batch_vectors)
        tokens += batch_tokens

    return vectors, tokens


def fingerprint(chunks: list[dict]) -> str:
    """
    the fingerprint changes if the text, the model or the order changes ... and stays put if nothing does
    """
    # SHA-256 : a recipe that turns any text into a fixed-length code (64 char)
    digest = hashlib.sha256(knowledge.EMBED_MODEL.encode())
    for c in chunks:
        digest.update(f"{c['id']}\n{c['text']}\n".encode())
    return digest.hexdigest()[
        :16
    ]  # hexdigest gives us the entire code , we are grabing the first 16 char from the code (magic number)


def build(startegy: str, force: bool = False) -> dict:
    """
    Makes sure the strategy's collection matches the current corpus, chunker, model
    ANSWERS ONE QUESTION : is the index I already have still correct?
    """
    # part 1 : check
    chunks = chunking.chunk_corpus(ALL_DOCUMENTS, startegy)
    fp = fingerprint(chunks)
    col = collection_for(startegy)
    stored = col.get(limit=1, include=["metadatas"])["metadatas"]

    if (
        not force
        and col.count() == len(chunks)
        and stored
        and stored[0].get("fingerprint") == fp
    ):
        return {
            "strategy": startegy,
            "chunks": len(chunks),
            "embedding_tokens": 0,
            "rebuilt": False,
        }

    # part 2 : rebuild
    #   Upsert would be fine only if you could guarantee chunk IDs are stable and the set never shrinks —
    # which isn't true when the chunking strategy, chunk size, or source corpus can change.
    # se we need to delete the collection
    # Drop the whole collection instead of upserting: chunk IDs/counts can change
    # across rebuilds (new corpus, different chunker), and upsert would leave
    # orphaned chunks from the previous build behind.
    try:
        chroma.delete_collection(collection_name(startegy))
    except Exception:
        pass

    col = collection_for(startegy)
    vectors, tokens = embed_batched([c["text"] for c in chunks], input_type="document")

    col.upsert(
        ids=[c["id"] for c in chunks],
        embeddings=vectors,
        documents=[c["text"] for c in chunks],
        metadatas=[
            {"doc_id": c["doc_id"], "title": c["title"], "fingerprint": fp}
            for c in chunks
        ],
    )
    # things to note:
    # embed_texts is imported not rewritten ... embedding provider has not changed only the storage has
    # configuration=.... -> not optional , we are choosing something different from default
    # chroma returns distance, we return similarity
    # in chroma lower is better
    # in our implementation higher is better
    # 1 - distance converts  it to similarity
    # upsert instead of add -> add fails on an id that already exists, upsert overwrites

    return {
        "strategy": startegy,
        "chunks": len(chunks),
        "embedding_tokens": tokens,
        "rebuilt": True,
    }


# search_with_vectors
# the read side
# it takes the question vectors that are already embeded , so enqueries are embeded once and reused across all 6 categories
def search_with_vectors(
    startegy: str, query_vectors: list[list[float]], k: int
) -> list[list[dict]]:
    # k: how many chunks to return per question
    """
    we embed the question once, then searches many strategies with the same vectors.
    """

    col = collection_for(startegy)
    if col.count() == 0:
        raise RuntimeError(f"Index for '{startegy}' is empty, build it first)")

    # the search
    result = col.query(query_embeddings=query_vectors, n_results=min(k, col.count()))
    # what result looks like
    # - result["ids"] - a list of 2 lists, each holding 3 ids
    # - result["documents"] - a list of 2 lists, each holding 3 texts
    # - result["metadatas"] - a list of 2 lists, each holding 3 metadata dictionaires
    # - result["diatances"] - a list of 2 lists, each holding 3 distances
    # e.g. ids            ['doc-001#00', 'doc-101#01', 'doc-107#00']
    # e.g. distances      [0.375, 0.389, 0.30]
    return [
        # chroma returns 4 parallel nested list
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


def cosine_for(
    strategy: str, query_vector: list[float], chunk_ids: list[str]
) -> dict[str, float]:
    if not chunk_ids:
        return {}

    stored = collection_for(strategy).get(ids=chunk_ids, include=["embeddings"])
    return {
        chunk_id : float(knowledge.cosine_similarity(query_vector, list(vector)))
        for chunk_id, vector in zip(stored["ids"], stored["embeddings"])
    }