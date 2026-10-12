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



def test_link_alerts_only_returns_open_alerts():
    """Only open alerts should be returned when filtering by open."""
    results = agent.link_alerts(1, status="open")
    assert len(results) > 0
    assert all(item["status"] == "open" for item in results)



def test_link_alerts_without_filter():
    """Linked alerts can have any status when no filter is supplied."""
    results = agent.link_alerts(1)

    assert isinstance(results, list)
    assert all("alert_id" in item for item in results)
    assert all("reasons" in item for item in results)


def test_link_alerts_tool_passes_status():
    """The agent tool forwards the status filter."""
    results, is_error = agent.execute_tool(
        "link_alerts",
        {"alert_id": 1, "status": "open"},
    )

    assert is_error is False
    assert len(results) > 0
    assert all(item["status"] == "open" for item in results)



def test_link_alerts_invalid_alert():
    """An unknown alert ID should return a tool error."""
    result, is_error = agent.execute_tool(
        "link_alerts",
        {"alert_id": 99999, "status": "open"},
    )

    assert is_error is True
    assert "not found" in result.lower()



def test_open_alerts_do_not_claim_counterparty_link_without_evidence():
    """Open linked alerts must report their actual relationship types."""
    results = agent.link_alerts(1, status="open")

    assert len(results) > 0

    for alert in results:
        assert alert["status"] == "open"
        assert alert["reasons"]

        # Each reason must describe a recognised relationship.
        for reason in alert["reasons"]:
            assert reason.startswith((
                "shared account(s):",
                "shared counterparty(s):",
                "shared corridor:",
            ))

    # Verify the known links for Alert 1.
    matches = {item["alert_id"]: item for item in results}

    assert "shared account(s): [3]" in matches[4]["reasons"]
    assert "shared account(s): [2]" in matches[6]["reasons"]

    assert not any(
        reason.startswith("shared counterparty(s):")
        for item in matches.values()
        for reason in item["reasons"]
    )

def test_relevant_documents_pass_threshold(monkeypatch):
    monkeypatch.setattr(
        agent.knowledge,
        "search",
        lambda query, top_k: [
            {
                "id": "doc-008",
                "title": "Structuring Guide",
                "score": 0.496,
                "text": "Review linked transactions.",
            }
        ],
    )

    results = agent.search_knowledge_base("structuring")

    assert len(results) == 1
    assert results[0]["id"] == "doc-008"


def test_irrelevant_documents_are_filtered(monkeypatch):
    monkeypatch.setattr(
        agent.knowledge,
        "search",
        lambda query, top_k: [
            {
                "id": "doc-006",
                "title": "Unrelated document",
                "score": 0.0784,
                "text": "Unrelated content.",
            }
        ],
    )

    results = agent.search_knowledge_base("Mars holidays")

    assert results == []
