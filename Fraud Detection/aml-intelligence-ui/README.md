# AML Intelligence Streamlit UI

This separate UI calls the real FastAPI project; it contains no hardcoded AI answers.

## Git Bash setup and launch

From the workspace root, in a second terminal:

```bash
cd "Fraud Detection/aml-intelligence-ui"
python -m venv .venv  # Only if it does not already exist
source .venv/Scripts/activate
python -m pip install -r requirements.txt
export AML_API_URL=http://127.0.0.1:8000
python -m streamlit run app.py
```

Start FastAPI first, following `../aml_intelligence_api/README.md`, and index with
`POST /knowledge/index`. The UI reads `AML_API_URL` from its process environment
(default `http://127.0.0.1:8000`). It does not require provider or reviewer keys;
those belong in the backend's local environment. Do not expose them in the UI.

## Pages and API contracts

| Page | API | Display |
|---|---|---|
| Home | `GET /health` | API connectivity |
| Ask | `POST /agent/ask` | Answer, tool names/calls, tokens, incomplete/clarification messages |
| Search Only | `GET /knowledge/search?q=...` | Every title and score; distinct unbuilt-index warning |
| Streaming Summary | `GET /alerts/{id}/summary/stream` | Progressively consumed text; advisory warning |
| Alert Queue | `GET /alerts/`, `POST /alerts/{id}/triage` | Filters and typed advisory triage |

The UI does not automatically close alerts. Human closure is explicitly requested
through the protected API described in the backend README. AI recommendations
do not change status. Record timing may be unknown; an alert creation date is not
a payment timestamp. Source similarity scores are not probabilities of correctness.

## Verification and troubleshooting

Run mocked UI/API contract checks using the API environment:

```bash
cd ../aml_intelligence_api
.venv/Scripts/python.exe -B -m pytest tests/test_ui_contracts.py -q -p no:cacheprovider
```

These tests mock Streamlit/provider operations, not real browser behaviour.
See the API `DEMO_GUIDE.md` for manual live verification. Never claim a live demo
passed solely because unit tests pass.

- API unavailable: start Uvicorn and check `AML_API_URL` and `/health`.
- Index-not-built warning: use the backend's `/knowledge/index` endpoint.
- 429/502/504: provider rate limit/failure/timeout; do not replace with fake answers.
- A stream interrupted after partial text may require retrying; already delivered
  text cannot be retracted or assigned a new HTTP status.
- Requests execute on the Streamlit server; no browser CORS setup is needed for this UI.
- Backend `.env` variables are not automatically loaded into this separate UI process.
