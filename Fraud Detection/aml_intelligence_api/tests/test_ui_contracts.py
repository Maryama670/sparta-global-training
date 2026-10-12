"""Execute UI page code with mocked Streamlit and in-process FastAPI HTTP.

This checks request/response contracts, not actual browser rendering.
"""
import runpy
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import requests
from fastapi.testclient import TestClient

from main import app
from routers import alerts, knowledge, agent_api


@pytest.mark.parametrize("page", ["1_Ask.py", "2_Search.py", "3_Streaming_Summary.py", "4_Alert_Queue.py"])
def test_ui_pages_use_existing_api_contracts(monkeypatch, page):
    st = MagicMock()
    st.button.return_value = True
    st.checkbox.return_value = False
    st.text_area.return_value = "Explain structuring investigation."
    st.text_input.return_value = "" if page == "4_Alert_Queue.py" else "structuring"
    st.number_input.return_value = 1
    st.selectbox.return_value = "All"
    monkeypatch.setitem(sys.modules, "streamlit", st)
    monkeypatch.setenv("AML_API_URL", "http://testserver")
    monkeypatch.setattr(agent_api, "ask_with_tools", lambda q: {
        "answer": "Review [doc-008].", "completed": False, "tools_used": [],
        "tool_calls_made": 0, "input_tokens": 10, "output_tokens": 2,
    })
    monkeypatch.setattr(knowledge, "index_is_built", lambda: True)
    monkeypatch.setattr(knowledge, "search", lambda q: [{"id": "doc-008", "title": "Guide", "score": .9}])
    def fake_stream(**kwargs):
        yield "Review "
        yield "evidence."
    monkeypatch.setattr(alerts, "stream_claude", fake_stream)
    monkeypatch.setattr(alerts, "ask_claude", lambda **kwargs: {"text": '{"decision":"request_information","likely_typology":"possible structuring","reasons":["Missing timing"],"evidence":["transaction 101"],"missing_information":["timestamps"]}'})
    calls = []
    with TestClient(app) as client:
        def request(method, url, **kwargs):
            calls.append((method, url))
            result = client.request(method, url, params=kwargs.get("params"), json=kwargs.get("json"))
            result.raise_for_status()
            wrapped = MagicMock()
            wrapped.status_code = result.status_code
            wrapped.json.return_value = result.json() if "application/json" in result.headers.get("content-type", "") else None
            wrapped.headers = result.headers
            wrapped.iter_content.return_value = iter([result.text])
            wrapped.__enter__.return_value = wrapped
            return wrapped
        monkeypatch.setattr(requests, "get", lambda url, **kw: request("GET", url, **kw))
        monkeypatch.setattr(requests, "post", lambda url, **kw: request("POST", url, **kw))
        runpy.run_path(str(Path(__file__).parents[2] / "aml-intelligence-ui" / "pages" / page))
    st.error.assert_not_called()
    assert calls
    if page == "1_Ask.py":
        assert calls[0][1].endswith("/agent/ask")
        st.warning.assert_any_call("Agent stopped before completing.")
    elif page == "2_Search.py":
        st.subheader.assert_any_call("Guide")
    elif page == "3_Streaming_Summary.py":
        assert "".join(st.write_stream.call_args.args[0]) == "Review evidence."
    else:
        assert any(url.endswith("/alerts/1/triage") for _, url in calls)


def test_search_ui_distinguishes_unbuilt_index(monkeypatch):
    st = MagicMock()
    st.button.return_value = True
    st.text_input.return_value = "structuring"
    class StopPage(Exception):
        pass
    st.stop.side_effect = StopPage
    monkeypatch.setitem(sys.modules, "streamlit", st)
    response = MagicMock(status_code=409)
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)
    with pytest.raises(StopPage):
        runpy.run_path(str(Path(__file__).parents[2] / "aml-intelligence-ui/pages/2_Search.py"))
    assert "not built" in st.warning.call_args.args[0]
    response.raise_for_status.assert_not_called()
