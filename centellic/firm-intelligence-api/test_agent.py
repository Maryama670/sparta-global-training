# 1. set up some fake building blocks
# 2. create a fake model  (that keeps going)
# 3. sub in our fake in step 2
# 4. hit our endpoint
# 5. check it stopped
# pretend the model never stops ... check your code stops it anyway
import agent
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class FakeToolUseBlock:
    type = "tool_use"
    id = "toolu_1"
    name = "search_knowledge_base"

    def __init__(self, input_: str):
        self.input = input_


class FakeUsage:
    def __init__(self, i, o):
        self.input_tokens, self.output_tokens = i, o


class FakeResponse:
    def __init__(self, content, stop_reason, usage):
        self.content, self.stop_reason, self.usage = content, stop_reason, usage


def test_agent_stops_at_max_itterations_instead_of_looping_forever(monkeypatch):
    def fake_create(**kworgs):
        return FakeResponse(
            [FakeToolUseBlock({"query": "anything"})], "tool_use", FakeUsage(100, 15)
        )

    monkeypatch.setattr(agent.client.messages, "create", fake_create)

    monkeypatch.setattr(
        agent.knowledge,
        "search",
        lambda query, top_k=3: [
            {
                "id": "doc_001",
                "title": "t",
                "text": "x",
                "score": 0.5,
            }
        ],
    )

    response = client.post("agent/ask", json={"question": "never resolves"})
    body = response.json()

    # assert completed
    assert body["complete"] == False

    # assert stop_reson
    assert body["stop_reason"] == "tool_use"

    # assert tool_calls_made
    assert body["tool_calls_made"] == 4