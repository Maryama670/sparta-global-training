# Chunking decision

**Review date:** 2026-10-13. **Corpus:** `documents.py` + `corpus.py`, 16 documents.
**Evaluation:** 32 questions, 29 answerable and three unanswerable.
**Embedding model in current code:** `voyage-3-lite`.

## Decision

Production provisionally uses **`section_contextual`** and the configured
`RELEVANCE_FLOOR` (default **0.35**). The strategy choice is supported by the saved
retrieval comparison; 0.35 is a retained tutorial baseline, **not an experimentally
validated optimal threshold**. Do not claim the saved answer run evaluated 0.35.

## Existing evidence

The following values are transcribed from the existing local
`eval_results/retrieval.json` and `eval_results/answers.json`; no paid evaluation
was rerun. Those files lack model/corpus fingerprints and run timestamps, so their
provenance and reproducibility cannot be independently established from JSON alone.
The answer file records **floor 0.55**, and only one strategy.

| Strategy | R@1 | R@3 | MRR@5 | Context words@3 | Answer accuracy at 0.55 | Refusal accuracy at 0.55 |
|---|---:|---:|---:|---:|---:|---:|
| whole_document | 0.690 | 1.000 | 0.845 | 862 | Not recorded | Not recorded |
| fixed_100 | 0.483 | 0.793 | 0.610 | 273 | Not recorded | Not recorded |
| fixed_overlap_25 | 0.517 | 0.931 | 0.668 | 277 | Not recorded | Not recorded |
| sentences_100 | 0.414 | 0.759 | 0.567 | 262 | Not recorded | Not recorded |
| sections_plain | 0.310 | 0.862 | 0.540 | 186 | Not recorded | Not recorded |
| section_contextual | 0.862 | 1.000 | 0.931 | 197 | 0.897 | 0.333 |

For contextual sections, the saved answer run lists false refusals **q06, q09,
q24**, incorrect unanswerable outcomes **q31, q32**, 29 generation calls, and
314 average input tokens per call. The reported accuracies correspond to
26/29 answerable questions and 1/3 unanswerable questions. This is weak refusal
performance; it does not justify promoting 0.55 as a reliable safety floor.

## Why contextual sections

In the saved retrieval comparison, contextual sections retrieve evidence in the
first result more often than whole documents (0.862 versus 0.690), retain R@3=1.000,
and use less context (197 versus 862 words at three results). Titles and headings
help disambiguate section prose. Whole documents also achieve R@3=1.000, so the
advantage here is first-result ranking and context size, not a universal recall win.
These are observations on this small evaluation set, not general guarantees.

## Production versus evaluation

- QA and agent use the shared environment-configured floor; default 0.35.
- Answer evaluation now defaults to that configuration but accepts `--floor`.
  The recorded historical answer run explicitly used 0.55.
- `floor_preview.py` previews thresholds 0.40?0.65 and reports gate-level refusals.
  It does not judge Claude answers or prove a retrieved document answers a question.
- QA and answer evaluation now both use `context.build_context()`: best chunk first,
  second best last. Previously production retained retrieval order. The agent
  continues to send scored tool results in retrieval order.
- Retrieval metrics test expected evidence spans. Answer accuracy remains keyword
  based, and refusal detection remains the exact normalised tutorial sentence or
  `None`. These scoring definitions were not changed to improve results.
- Production now withholds invalid citations. Historical answer accuracy does not
  incorporate those new acceptance checks and must not be presented as current
  end-to-end production accuracy. Valid citations still do not prove claim support.

## Known weaknesses and next evidence

The three unanswerable cases are too few to establish robust refusal behaviour.
Keyword checks may accept contradictory/extra claims or reject legitimate wording.
Scores are similarities, not probabilities. Evaluation assumes one complete result
group per question; malformed groups now fail instead of silently truncating.

Before changing the floor, rerun explicit live comparisons under approved provider
use, record the actual model/version, corpus fingerprint, date and configuration,
and manually review both false refusals and unsupported answers. Evaluate more
unanswerable and ambiguous questions. Revisit the strategy when document shape,
corpus size or embedding model changes. No live calibration was performed here.

**Deferred storage risk:** the existing Chroma rebuild deletes before embedding
succeeds. This was deliberately not refactored in the current task.
