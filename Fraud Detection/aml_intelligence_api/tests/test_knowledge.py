from fastapi.testclient import TestClient

from main import app
from routers import knowledge as knowledge_routes


client = TestClient(app)


def test_low_score_refuses_without_calling_claude(monkeypatch):
    fake_results = [
        {
            "id": "doc-999",
            "title": "Irrelevant document",
            "score": 0.10,
            "text": "This does not answer the question.",
        }
    ]

    monkeypatch.setattr(
        knowledge_routes,
        "search",
        lambda query, top_k=3: fake_results,
    )

    called = {"value": False}

    def fake_ask_claude(*args, **kwargs):
        called["value"] = True
        return {
            "text": "This should never be called",
            "input_tokens": 10,
            "output_tokens": 10,
        }

    monkeypatch.setattr(
        knowledge_routes,
        "ask_claude",
        fake_ask_claude,
    )

    response = client.post(
        "/knowledge/ask",
        json={"question": "What is the best mortgage rate?"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["document_ids"] == []
    assert body["input_tokens"] == 0
    assert body["output_tokens"] == 0
    assert called["value"] is False

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
import knowledge_store


def match(doc_id="doc-008", score=0.8):
    return {"id": doc_id, "title": "Procedure", "text": "Review linked transactions.", "score": score}


@pytest.mark.parametrize("matches", [[], [match(score=0.1)]])
def test_no_relevant_evidence_never_calls_claude(monkeypatch, matches):
    monkeypatch.setattr(knowledge_routes, "search", lambda query: matches)
    provider = MagicMock(side_effect=AssertionError("Claude must not be called"))
    monkeypatch.setattr(knowledge_routes, "ask_claude", provider)
    response = client.post("/knowledge/ask", json={"question": "Unsupported question"})
    assert response.status_code == 200
    assert response.json()["answer"] == knowledge_routes.INSUFFICIENT_EVIDENCE
    assert response.json()["document_ids"] == []
    provider.assert_not_called()


def test_filters_each_hit_and_returns_only_cited_sources(monkeypatch):
    monkeypatch.setattr(knowledge_routes, "RELEVANCE_FLOOR", 0.35)
    monkeypatch.setattr(knowledge_routes, "search", lambda query: [match("doc-001", 0.1), match(score=0.35), match("doc-003")])
    provider = MagicMock(return_value={"text": "Review transactions [doc-008].", "input_tokens": 20, "output_tokens": 6})
    monkeypatch.setattr(knowledge_routes, "ask_claude", provider)
    response = client.post("/knowledge/ask", json={"question": "What should I review?"})
    assert response.status_code == 200
    assert response.json()["document_ids"] == ["doc-008"]
    assert response.json()["input_tokens"] == 20
    kwargs = provider.call_args.kwargs
    assert "DOCUMENT ID: doc-001" not in kwargs["user_message"]
    assert "DOCUMENT ID: doc-008" in kwargs["user_message"]
    assert "DOCUMENT ID: doc-003" in kwargs["user_message"]
    assert "square brackets" in kwargs["system_prompt"]


@pytest.mark.parametrize("answer", ["Uncited answer.", "Unknown [doc-999].", "Mixed [doc-008] [doc-999]."])
def test_missing_or_unknown_citations_are_rejected(monkeypatch, answer):
    monkeypatch.setattr(knowledge_routes, "search", lambda query: [match()])
    monkeypatch.setattr(knowledge_routes, "ask_claude", lambda **kwargs: {"text": answer, "input_tokens": 10, "output_tokens": 4})
    assert client.post("/knowledge/ask", json={"question": "Procedure?"}).status_code == 502


def test_model_can_refuse_when_relevant_documents_do_not_answer(monkeypatch):
    monkeypatch.setattr(knowledge_routes, "search", lambda query: [match()])
    monkeypatch.setattr(knowledge_routes, "ask_claude", lambda **kwargs: {"text": knowledge_routes.INSUFFICIENT_EVIDENCE, "input_tokens": 10, "output_tokens": 4})
    response = client.post("/knowledge/ask", json={"question": "Procedure?"})
    assert response.status_code == 200
    assert response.json()["document_ids"] == []
    assert response.json()["input_tokens"] == 10


def test_search_uses_voyage_query_vectors_and_chroma_scores(monkeypatch):
    voyage = MagicMock()
    voyage.embed.return_value = SimpleNamespace(embeddings=[[0.1, 0.2]])
    collection = MagicMock()
    collection.count.return_value = 1
    collection.query.return_value = {"ids": [["doc-008"]], "metadatas": [[{"title": "Procedure"}]], "documents": [["Review transactions."]], "distances": [[0.2]]}
    monkeypatch.setattr(knowledge_store, "voyage_client", voyage)
    monkeypatch.setattr(knowledge_store, "collection", collection)
    results = knowledge_store.search("structuring", top_k=3)
    voyage.embed.assert_called_once_with(["structuring"], model=knowledge_store.VOYAGE_MODEL, input_type="query")
    collection.query.assert_called_once_with(query_embeddings=[[0.1, 0.2]], n_results=1)
    assert results[0]["score"] == pytest.approx(0.8)
    assert results[0]["id"] == "doc-008"


def test_empty_index_does_not_call_embedding_provider(monkeypatch):
    voyage = MagicMock()
    collection = MagicMock()
    collection.count.return_value = 0
    monkeypatch.setattr(knowledge_store, "voyage_client", voyage)
    monkeypatch.setattr(knowledge_store, "collection", collection)
    assert knowledge_store.search("anything") == []
    voyage.embed.assert_not_called()
    collection.query.assert_not_called()
