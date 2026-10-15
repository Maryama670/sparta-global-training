import anthropic  # Load the Anthropic SDK, including its model client and exception classes.
from fastapi.testclient import TestClient  # Import the HTTP test client used to call application routes without a running server.

import llm  # Load this project's model helpers and client; access them with the llm. prefix.
from main import app  # Import the FastAPI application so tests can send requests to its routes.


client = TestClient(app)  # Create a local HTTP test client for the FastAPI application.

FAKE_SUMMARY = {  # Define a fixed model response used by tests.
    "id": 1,  # Include the record identifier in this record.
    "name": "Harding & Voss",  # Include the name in this record.
    "summary": "A fixture company",  # Include the generated summary in this record.
    "input_tokens": 120,  # Include the input token count in this record.
    "output_tokens": 95,  # Include the output token count in this record.
    "stop_reason": "end_turn",  # Include the reason generation stopped in this record.

}  # Close the preceding expression or collection.

#test
#what paths could the call

def test_summary_returns_text_and_summary(monkeypatch):  # Check the summary endpoint status and reported input tokens.
    monkeypatch.setattr(llm, "summarise_firm", lambda firm: FAKE_SUMMARY)  # Replace this model helper for the duration of the test, avoiding a real provider call.
    response = client.post("/firms/1/summary")  # Send a local test request to the specified API endpoint.
    # Assert what it should do.
    assert response.status_code == 200  # Fail the test unless response.status_code equals 200.
    assert response.json()["input_tokens"] == 120  # Fail the test unless response.json()["input_tokens"] equals 120.



def test_provider_timeout_becomes_504(monkeypatch):  # Check that a provider timeout is returned as HTTP 504.
    def boom(firm):  # Provide a test replacement that always raises a timeout.
        raise anthropic.APITimeoutError(request=None)  # Simulate a provider timeout for the error-handling test.

    monkeypatch.setattr(llm, "summarise_firm", boom)  # Replace this model helper for the duration of the test, avoiding a real provider call.
    response = client.post("/firms/1/summary")  # Send a local test request to the specified API endpoint.
    assert response.status_code == 504  # Fail the test unless response.status_code equals 504.


#check that our estimate does not call the model
def test_estimate_does_not_call_the_model(monkeypatch):  # Test the estimate endpoint using a replacement token counter.
    monkeypatch.setattr(llm, "estimate_input_tokens", lambda firm: 137)  # Replace this model helper for the duration of the test, avoiding a real provider call.
    response = client.get("/firms/1/summary/estimate")  # Send a local test request to the specified API endpoint.

    #assertions
    assert response.status_code == 200  # Fail the test unless response.status_code equals 200.
    assert response.json()["estimated_input_tokens"] == 137  # Fail the test unless response.json()["estimated_input_tokens"] equals 137.


def test_stream_yields_chunks(monkeypatch):  # Test how the endpoint streams and combines summary chunks.
    monkeypatch.setattr(llm, "stream_firm_summary", lambda firm: iter(["Hard", "ing ", "& Voss"]))  # Replace the streaming helper without calling the provider.
    with client.stream("GET", "firms/1/summary/stream") as response:  # Open a streamed test request and close it when the block ends.
        assert response.status_code ==200  # Fail the test unless response.status_code equals200.
        body = "".join(response.iter_text())  # Combine the streamed response chunks into one string.
    assert body == "Harding & Voss"  # Fail the test unless body equals "Harding & Voss".



    

    #response = client.post("firms")...





