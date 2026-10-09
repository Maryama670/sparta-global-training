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