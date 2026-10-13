# Firm Intelligence API

Tutorial FastAPI service with synthetic law-firm/person records, Claude summaries
and structured analysis, Voyage embeddings, persistent Chroma retrieval, a bounded
search agent and six chunking strategies.

## Setup and run (Windows Git Bash)

Python **3.12+** is required by the source syntax. From the workspace root:

```bash
cd centellic/firm-intelligence-api
python -m venv .venv  # Only if an environment does not already exist
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

The pinned direct dependencies match the existing virtual environment. A fresh
installation has not been tested during this offline work.

Set `ANTHROPIC_API_KEY` and `VOYAGE_API_KEY` privately in your terminal environment
before starting. Do not put credentials in source, screenshots, prompts or commits.
The current application reads process variables at import time; it does **not**
automatically load `.env` files.

| Configuration | Current setting |
|---|---|
| `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY` | Required environment variables |
| `RELEVANCE_FLOOR` | Optional environment variable, default `0.35`, range 0–1 |
| Claude model | `claude-haiku-4-5-20251001` in `llm.py` |
| Voyage model | `voyage-3-lite` in `knowledge.py` |
| Production strategy | `section_contextual` in `knowledge_store.py` |
| Agent limit | Four model turns; tool count records successful calls |

```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Run from this directory because Chroma uses `./chroma_store`. Swagger is at
http://127.0.0.1:8000/docs. **Real startup may call Voyage and write Chroma.**
The tutorial's startup indexing is preserved with FastAPI lifespan; unchanged
fingerprints reuse stored chunks without fresh document embeddings.

## Endpoints and evidence flow

| Route | Purpose |
|---|---|
| `GET /health` | Service status |
| `/firms`, `/people` | Tutorial record operations/filters; see Swagger |
| `POST /firms/{id}/summary` | Claude summary and usage |
| `GET /firms/{id}/summary/estimate` | Input token estimate |
| `GET /firms/{id}/summary/stream` | Plain-text provider stream |
| `POST /firms/{id}/analysis` | Pydantic-validated analysis |
| `POST /knowledge/index` | Build/reuse the selected chunk index |
| `POST /knowledge/search` | Retrieval only |
| `POST /knowledge/ask` | Grounded answer or refusal |
| `POST /agent/ask` | Bounded read-only search agent |

Knowledge requests use `{"question":"revenue growth","top_k":3}`. Agent requests
use `{"question":"What do the reports say about revenue growth?"}`.

The 16 documents in `documents.py` plus `corpus.py` are chunked, embedded and stored
in a strategy-specific Chroma collection. A query vector finds chunks using cosine
distance. `1 - distance` is similarity, not a correctness probability. Results
retain parent document IDs and chunk IDs.

QA filters every hit before generation. No qualifying evidence means refusal
without Claude. QA and answer evaluation both use `context.build_context()` to
label and reorder chunks. Invalid citations withhold answers (`answer=null`,
`refused=true`) while retaining the grounding report and generation usage. Model
refusals also return `refused=true` with no sources. Citation checking verifies
reference validity and sentence coverage, **not semantic support for every claim**.

The agent validates tool input, filters evidence and returns tool failures safely.
After searching, final answers require retrieved-source citations; absent evidence
causes refusal. Source IDs come from structured results, never IDs mentioned inside
document bodies. To preserve the tutorial, general answers made without searching
remain available without citations; invented document citations are rejected.

Knowledge/agent provider failures map to 504 for timeout, 429 for rate limit and
502 for upstream failure. Empty indexes produce 409. Errors do not echo provider
bodies. An error after streaming response headers interrupts the stream; a fresh
HTTP error status cannot be sent after partial delivery.

## Offline verification

```bash
python -B -m pytest -q -p no:cacheprovider
python -m pip check
git diff --check -- .
```

`conftest.py` replaces Claude/Voyage constructors and persistent Chroma before
test collection. Unit tests need no live keys, requests or database writes. Startup
tests exercise real build/reuse control flow with mocked storage. Eight regression
tests are restored. The legacy in-memory rebuild test covers `knowledge.INDEX`,
not the persistent Chroma rebuild sequence.

## Evaluation — explicit live operation

These commands can incur costs, rebuild indexes and overwrite generated outputs.
Do not run them as offline checks:

```bash
python -B -m eval_retrieval
python -B -m floor_preview
python -B -m eval_answers section_contextual --floor 0.55
```

The six strategies are `whole_document`, `fixed_100`, `fixed_overlap_25`,
`sentences_100`, `sections_plain`, `section_contextual`. The evaluation has 32
questions: 29 answerable and three unanswerable. Retrieval reuses question vectors
across collections. Recall checks expected evidence spans; the `mrr` field is
MRR@5 because only five results are retrieved. Malformed result groups fail
explicitly instead of silently truncating.

Answer scoring preserves its definitions: all keyword groups must match, and only
the exact normalised refusal sentence or `None` counts as refusal. Answerable
refusals are listed in `false_refusals`; wrong non-refusals and incorrect
unanswerable responses are in historical `wrong_or_refused`. Average tokens measure
input tokens per generation, excluding embedding/output costs and full experiment cost.

QA/agent share the configured floor (default 0.35). Answer evaluation defaults to
it but permits `--floor`. The historical saved answer run used **0.55**, not 0.35.
`floor_preview` deliberately compares 0.40–0.65. QA and answer evaluation now share
context ordering, while the agent sends scored tool context in retrieval order.
Keyword scoring is not production citation acceptance. Historical answer scores
predate the new enforcement; no fresh live results were produced. Read
`Docs/chunking-decision.md` for the saved metrics and their limitations.

Optional experiments run as modules, for example
`python -m experiments.lost_in_the_middle --help`; these are not production routes.

## Remaining limits and Git hygiene

- **Chroma rebuild is deliberately not refactored:** it deletes the selected
  collection before embedding succeeds. A failure may lose the previous index.
  Atomic rebuilds remain deferred; the legacy in-memory test does not protect Chroma.
- Missing provider environment variables prevent imports/startup. Set them before launch.
- Changing embedding models or corpus requires reviewing/rebuilding the index.
- Structured records are in memory; this is a tutorial service, not a hardened deployment.
- Live service operation, browser streaming and clean installation remain unverified.
- An upstream Starlette/AnyIO warning and a local `~ip` distribution warning remain;
  they are not suppressed or presented as fixed.

Commit source, tests, dependencies and documentation after review. The project
`.gitignore` excludes secrets, environments, Chroma data, generated evaluation JSON
and raw probe/run notes. Summarised historical evidence is retained in Docs. Do not
stage unrelated projects or use repository-wide `git add .`.
