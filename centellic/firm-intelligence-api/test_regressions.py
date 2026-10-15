from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest
import httpx
import anthropic
import knowledge
import knowledge_store
import llm
import main
from routers import agent, people
from fastapi.testclient import TestClient


def test_shared_index():
    assert agent.knowledge is knowledge_store
    assert main.build_index is knowledge_store.build_index


def test_first_person(monkeypatch):
    monkeypatch.setattr(people, "PEOPLE", [])
    person = people.add_person(people.NewPerson(name="Sam", role="Partner", firm_id=1))
    assert person["id"] == 1


def test_vectors():
    assert knowledge.cosine_similarity([0.0], [1.0]) == 0.0
    assert knowledge.cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    with pytest.raises(ValueError):
        knowledge.cosine_similarity([1.0], [1.0, 2.0])


def test_failed_rebuild_keeps_index(monkeypatch):
    old = [{"id": "old"}]
    monkeypatch.setattr(knowledge, "INDEX", old.copy())
    monkeypatch.setattr(knowledge, "embed_text", Mock(side_effect=RuntimeError("Unavailable")))
    with pytest.raises(RuntimeError):
        knowledge.build_index()
    assert knowledge.INDEX == old


def test_empty_store_does_not_embed(monkeypatch):
    monkeypatch.setattr(knowledge_store, "count", lambda: 0)
    embed = Mock()
    monkeypatch.setattr(knowledge_store, "embed_text", embed)
    with pytest.raises(RuntimeError, match="Index is empty"):
        knowledge_store.search("firm")
    embed.assert_not_called()


def test_parsed_analysis(monkeypatch):
    parsed = llm.FirmAnalysis(tier="boutique", strengths=[], risks=[], headcount_efficiency="high")
    response = NS(parsed_output=parsed, content=[], usage=NS(input_tokens=10, output_tokens=5), stop_reason="end_turn")
    monkeypatch.setattr(llm.client.messages, "parse", Mock(return_value=response))
    assert llm.analyse_firm(main.firms.FIRMS[0])["analysis"] == parsed
    response.parsed_output = None
    with pytest.raises(ValueError):
        llm.analyse_firm(main.firms.FIRMS[0])


def test_connection_error_is_502(monkeypatch):
    error = anthropic.APIConnectionError(request=httpx.Request("POST", "https://example.test"))
    monkeypatch.setattr(llm, "summarise_firm", Mock(side_effect=error))
    assert TestClient(main.app).post("/firms/1/summary").status_code == 502


def test_agent_multiple_results_and_limit(monkeypatch):
    def response(reason, content):
        return NS(stop_reason=reason, content=content, usage=NS(input_tokens=10, output_tokens=5))
    tool = response("tool_use", [NS(type="tool_use", id="one", name="search_knowledge_base", input={"query": "firm"}), NS(type="tool_use", id="two", name="unknown", input={})])
    final = response("end_turn", [NS(type="text", text="Answer")])
    create = Mock(side_effect=[tool, final])
    monkeypatch.setattr(agent.client.messages, "create", create)
    monkeypatch.setattr(agent.knowledge, "search", Mock(return_value=[]))
    result = agent.ask_with_tools("Question")
    assert result["completed"] and result["input_tokens"] == 20
    results = create.call_args.kwargs["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["one", "two"]
    assert results[1]["is_error"] is True
    create.side_effect = [tool] * agent.MAX_ITERATIONS
    assert agent.ask_with_tools("Question")["stop_reason"] == "max_iterations"
