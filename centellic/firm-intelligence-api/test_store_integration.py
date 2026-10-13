"""Regression coverage for the production strategy and embedding API wiring."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

import chunk_index
import chunking
import knowledge
import knowledge_store
import main


def test_production_strategy_is_registered():
    assert knowledge_store.CHUNK_STRATEGY == "section_contextual"
    chunks = chunking.chunk_corpus(chunk_index.ALL_DOCUMENTS, knowledge_store.CHUNK_STRATEGY)
    assert chunks
    assert {c["doc_id"] for c in chunks} == {d["id"] for d in chunk_index.ALL_DOCUMENTS}


def test_search_uses_existing_embedding_api_and_vector_batch(monkeypatch):
    monkeypatch.setattr(knowledge_store, "count", lambda: 1)
    vectors = [[0.1, 0.2, 0.3]]
    provider = Mock(return_value=SimpleNamespace(embeddings=vectors, total_tokens=7))
    monkeypatch.setattr(knowledge.voyage, "embed", provider)
    hits = [{"id": "doc-101", "chunk_id": "doc-101#00", "text": "Evidence", "score": .8}]
    search = Mock(return_value=[hits])
    monkeypatch.setattr(chunk_index, "search_with_vectors", search)
    assert knowledge_store.search("Explain revenue growth", top_k=2) == hits
    provider.assert_called_once_with(
        texts=["Explain revenue growth"], model=knowledge.EMBED_MODEL, input_type="query"
    )
    search.assert_called_once_with("section_contextual", vectors, k=2)


@pytest.mark.parametrize("cached", [False, True])
def test_application_startup_builds_or_reuses_selected_index_offline(monkeypatch, cached):
    # Exercise the real startup -> store -> chunk_index chain, with storage mocked.
    chunks = chunking.chunk_corpus(chunk_index.ALL_DOCUMENTS, "section_contextual")
    collection = Mock()
    collection.count.return_value = len(chunks) if cached else 0
    collection.get.return_value = {"metadatas": [
        {"fingerprint": chunk_index.fingerprint(chunks)}
    ] if cached else []}
    chroma = Mock()
    chroma.get_or_create_collection.return_value = collection
    monkeypatch.setattr(chunk_index, "chroma", chroma)
    embed = Mock(return_value=([[.1, .2] for _ in chunks], 123))
    monkeypatch.setattr(knowledge, "embed_text", embed)
    with TestClient(main.app) as client:
        assert client.get("/health").json() == {"status": "ok"}
    assert chroma.get_or_create_collection.call_args.kwargs["name"] == "chunks_section_contextual"
    if cached:
        embed.assert_not_called()
        collection.upsert.assert_not_called()
        chroma.delete_collection.assert_not_called()
    else:
        embed.assert_called_once()
        assert embed.call_args.kwargs["input_type"] == "document"
        assert collection.upsert.call_args.kwargs["ids"] == [c["id"] for c in chunks]
