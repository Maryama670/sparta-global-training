# AML Intelligence — live demo checklist

**Status:** prepared examples, not a record of successful live execution.
Unit tests use mocks. Real Claude/Voyage calls incur costs and require working keys.

## Start services (Git Bash, two terminals)

From the workspace root:

```bash
cd "Fraud Detection/aml_intelligence_api"
source .venv/Scripts/activate
python -m uvicorn main:app --reload --port 8000
```

```bash
cd "Fraud Detection/aml-intelligence-ui"
source .venv/Scripts/activate
export AML_API_URL=http://127.0.0.1:8000
python -m streamlit run app.py
```

Use each README for installation/environment setup. In Swagger at
http://127.0.0.1:8000/docs, check `/health`, then `POST /knowledge/index`.
Expected indexed-document count: **8**. Do not label it verified until observed.

## Demonstrate both tools

On Ask, enter:

> For Alert 1, use link_alerts with status=open to find related open alerts.
> Explain the actual relationship types, not just counterparty links. Then use
> search_knowledge_base to explain the structuring investigation procedure,
> citing supporting documents. Separate recorded facts, guidance and recommendations.

Seeded facts: Alert 1 has payments 101/102/103 from accounts 1/2/3 to counterparty 1,
Desert Star Trading. Open Alert 4 shares account 3; open Alert 6 shares account 2.
Neither shares counterparty 1. Alert 5 shares counterparty 1 but is under_review,
so it must not appear as an open result. This is why the prompt asks for actual
relationship types. The broad question "which open alerts share a counterparty"
does not have a positive seeded pair here.

Check `tools_used` includes both tool names and `tool_calls_made` counts attempts.
Check input/output usage, citations such as `[doc-008]` when actually retrieved,
and no invented transaction timing or intent. Tool choice is model-dependent;
if it fails to use both, record that failure and investigate rather than claiming success.

## Demonstrate refusal and clarification

Ask:

> What is the holiday policy for a trip to Mars?

Expected: no relevant AML evidence and an insufficient-evidence answer. Observe
actual scores: unrelated documents may still clear a poorly calibrated threshold.
For direct `/knowledge/ask`, verify zero Claude tokens only when no result clears
the floor. The agent itself usually needs a Claude turn to choose its search tool.
A high-scoring but non-answering result must not be treated as proof of an answer.

Ask "What should I do?". Expected: clarification before retrieval or Claude, zero
tool calls/tokens. This checks the explicit generic-question guard, not every ambiguity.

## Other compulsory demonstrations

1. Search Only: title and score for every result. An empty index must show a distinct
   index-not-built warning. Use a separate empty demo index/environment if needed;
   do not delete the working index just for the demo.
2. Streaming Summary for Alert 1: observe progressive text. It must distinguish
   unknown payment timing from `created_at`. Browser progression is a live check.
3. Alert Queue: filter open alerts; request triage. Confirm status is unchanged.
4. Swagger ordinary PUT with `status=closed`: expect 403. Protected closure requires
   explicit human review, an active reviewer ID, justification and `X-Reviewer-Key`.
   Configure the key privately; never paste it into Ask or screenshots. Closing an
   alert changes in-memory data, so do this only as the deliberate human demo action.
5. Show `/tokens/estimate` and explain approximate versus actual provider usage.
6. Explain the four-iteration limit and show a clear incomplete result from tests.

## Explain the pipeline

Streamlit sends HTTP to FastAPI. Knowledge search sends query text to Voyage,
then sends its vector to persistent Chroma. Chroma returns stored prose, metadata
and distances. The floor filters evidence. Claude receives rules in its system
message and evidence in user/tool messages. Citation checks restrict referenced
IDs. The linked-alert tool computes relationships locally, without embeddings.
Neither tool can close an alert; only the protected human endpoint can.

## Capture honest evidence before hand-in

Record actual date/settings, index count, representative search scores, answer,
citations, both tool names, tokens, refusal and unchanged status after triage.
Run `python -m eval_thresholds --output threshold_results.json` after indexing to
record threshold comparisons, then complete the design note with real observations.
Do not include keys, `.env`, or private provider errors. A successful mocked test
is not evidence of live model access, answer accuracy or browser rendering.
