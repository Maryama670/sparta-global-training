# 1. Set up some fake building blocks.
# 2. Create a fake model that keeps going.
# 3. Substitute our fakes for the real dependencies.
# 4. Hit our endpoint.
# 5. Check it stopped.
# Pretend the model never stops; check our code stops it anyway.

from fastapi.testclient import TestClient

from main import app
from routers import agent

client = TestClient(app)


class FakeToolUseBlock:
    type = "tool_use"
    id = "toolu_01"
    name = "search_knowledge_base"

    def __init__(self, input_):
        self.input = input_


class FakeUsage:
    def __init__(self, i, o):
        self.input_tokens, self.output_tokens = i, o


class FakeResponse:
    def __init__(self, content, stop_reason, usage):
        self.content, self.stop_reason, self.usage = content, stop_reason, usage





def test_agent_stops_at_max_iterations_instead_of_looping_forever(monkeypatch):
    # **kwargs accepts named arguments such as model, messages and tools.
    # We ignore them: this fake always asks for another search, never an answer.
    def fake_create(**kwargs):
        return FakeResponse(
            [FakeToolUseBlock({"query": "anything"})], "tool_use", FakeUsage(100, 15)
        )

    # Replace the real model method with our function (do not call it here).
    # pytest supplies monkeypatch and restores these replacements after the test.
    monkeypatch.setattr(agent.client.messages, "create", fake_create)
    # lambda is a small function: accept the search arguments and return one hit.
    # This avoids real searches/embeddings and makes every tool call successful.
    monkeypatch.setattr(
        agent.knowledge, "search",
        lambda q, top_k=3: [{"id": "doc-001", "title": "t", "text": "x", "score": 0.5}],
    )

    # TestClient sends the request inside Python; no running web server is needed.
    # The real endpoint and agent loop run, using our fake model and search.
    response = client.post("/agent/ask", json={"question": "never resolve"})
    assert response.status_code == 200
    # Decode the response JSON so we can read its fields with dictionary keys.
    body = response.json()

    # assert means "this must be true"; otherwise pytest marks the test as failed.
    # completed must be False: stopping at the limit is not a finished answer.
    assert body["completed"] is False

    # The agent must report that its own limit stopped it.
    # The fake model only returns "tool_use", so this reason comes from our code.
    assert body["stop_reason"] == "max_iterations"

    # Each loop runs one successful search, so the count must equal the limit.
    # Read the constant rather than hard-coding 4, in case the limit changes.
    assert body["tool_calls_made"] == agent.MAX_ITERATIONS
