from types import SimpleNamespace

import agent


class FakeUsage:
    input_tokens = 100
    output_tokens = 25


class FakeToolBlock:
    type = "tool_use"
    name = "search_knowledge_base"
    id = "tool-1"
    input = {"query": "structuring"}


class FakeResponse:
    stop_reason = "tool_use"
    content = [FakeToolBlock()]
    usage = FakeUsage()


def test_agent_stops_at_max_iterations(monkeypatch):
    monkeypatch.setattr(agent, "MAX_ITERATIONS", 1)

    fake_client = SimpleNamespace()
    fake_client.messages = SimpleNamespace()
    fake_client.messages.create = lambda **kwargs: FakeResponse()

    monkeypatch.setattr(agent, "client", fake_client)

    monkeypatch.setattr(
        agent,
        "execute_tool",
        lambda name, tool_input: ("fake result", False),
    )

    result = agent.ask_with_tools(
        "What does the procedure say about structuring?"
    )

    assert result["completed"] is False
    assert result["answer"] is None
    assert result["stop_reason"] == "max_iterations"
    assert result["tool_calls_made"] == 1