# AML Intelligence API — Option F

Synthetic fraud/AML investigation support using FastAPI, Claude, Voyage and
persistent Chroma. AI recommends; only the protected human action can close an alert.

## Git Bash setup

From the workspace root (Python 3.12+; the existing environment was tested with 3.14):

```bash
cd "Fraud Detection/aml_intelligence_api"
python -m venv .venv  # Only if an environment does not already exist
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

Create a local `.env` using your editor. Never share it, log it or commit it.
Set `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` to your own credentials. Set
`AML_REVIEWER_KEY` to a separate, long random credential for authorised human review.
Do not put the reviewer credential in Claude messages or agent tools.

| Environment variable | Default / purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required for Claude features; missing key returns 503 |
| `VOYAGE_API_KEY` | Required for indexing/query embeddings; missing key returns 503 |
| `CLAUDE_MODEL` | `claude-haiku-4-5-20251001` |
| `CLAUDE_TIMEOUT` | `30` seconds |
| `VOYAGE_MODEL` | `voyage-3-lite`; rebuild/recreate the index when changing embedding models |
| `RELEVANCE_FLOOR` | `0.35`, shared by knowledge QA and agent search; provisional |
| `AGENT_MAX_ITERATIONS` | `4`, maximum model turns, not individual tool calls |
| `AML_REVIEWER_KEY` | No default; closure returns 503 until configured |

Run from this API directory, because Chroma uses `./chroma_store`:

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/docs. Start the UI in a second terminal using its README.

## Index and API workflow

These commands require the server. Indexing and questions can incur provider costs.

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS -X POST http://127.0.0.1:8000/knowledge/index
curl -fsS -G http://127.0.0.1:8000/knowledge/search --data-urlencode 'q=structuring investigation'
curl -fsS -H 'Content-Type: application/json' -d '{"question":"What evidence is needed before recommending an alert outcome?"}' http://127.0.0.1:8000/knowledge/ask
```

`POST /knowledge/index` embeds the eight Markdown documents and upserts by ID.
It currently re-embeds on each invocation; it is not a free cached operation.
`GET /knowledge/search?q=...` returns titles and similarity scores, with 409
`index_not_built` when the collection is empty. `/knowledge/ask` refuses without
Claude if no result clears the floor. Accepted answers require retrieved-source
citations; valid citations do not prove every claim is true.

Other endpoints: `/alerts/` and `/accounts/` provide CRUD and filters;
`POST /alerts/{id}/summary`, `GET /alerts/{id}/summary/stream`,
`POST /alerts/{id}/triage`, and `POST /agent/ask` provide AI support.
Triage decisions are `escalate`, `request_information` or `recommend_closure`.

## Human closure

In Swagger, use Authorize for `X-Reviewer-Key`, then `POST /alerts/{id}/close` with
an active `reviewer_id` and a meaningful `reason` (10–1,000 characters after trimming
for the minimum). Ordinary create/update cannot set `closed`; ordinary reopening
and deletion of closed alerts are also blocked. The agent has no closure tool.
Do not pass the reviewer credential to the model.

Closure audit entries record alert ID, named reviewer ID, reason, UTC time and
previous/new status. **The shared credential is prototype security, not verified
individual identity. Records and audit entries are in memory and reset on restart.**
Chroma documents persist separately. Case status is not automatically changed by
alert closure. This is a local coursework prototype, not a production AML system.

## Tokens and tests

Summary, QA and agent return actual provider input/output token usage. Streaming
and triage preserve their existing response contracts. `POST /tokens/estimate`
accepts `{"text":"text to estimate"}` and provides an explicitly approximate,
offline byte-length estimate. It excludes hidden framing/system/tool overhead and
must not be used as exact billing data.

```bash
python -B -m pytest -q -p no:cacheprovider
```

Tests mock Claude, Voyage, Chroma and Streamlit; UI contract tests run pages against
in-process FastAPI. They do not verify browser rendering or real provider quality.
No unit test needs real credentials or a live service.

Optional **live** threshold comparison, after indexing (Voyage and Chroma only):

```bash
python -B -m eval_thresholds --output threshold_results.json
```

Review source hits and unsupported admissions at each floor. Inspect cases manually:
similarity is not answerability. No calibration results have been claimed or bundled.
See `DESIGN_NOTE.md` and `DEMO_GUIDE.md` for limitations and the live checklist.

## Troubleshooting

- 503: configure the named provider/reviewer variable and restart the process.
- 409 `index_not_built`: index the knowledge documents first.
- 429: wait/reduce traffic; 504: provider timeout; 502: upstream failure or invalid citations/output.
- A provider error during a stream after headers are sent interrupts the stream;
  a new HTTP status cannot be sent at that point. Retry after checking the provider.
- An insufficient-evidence answer is deliberate; do not lower the floor just to force an answer.
- Generic prompts request clarification. Ambiguity detection covers common explicit
  vague phrases and is not a complete natural-language intent detector.
- Run commands in the intended project and activate its environment. Use
  `.venv/Scripts/python.exe` explicitly if your PATH chooses a different interpreter.
- Missing Chroma query results after switching directories can mean a different
  relative `chroma_store` was opened. Embedding model changes require a compatible rebuilt index.
