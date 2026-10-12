# AML Intelligence — design note

**Scope.** Synthetic Option F investigation support. The platform separates recorded
alert/account/payment/counterparty facts, retrieved internal guidance, and advisory
AI recommendations. It does not establish criminal intent or make final compliance decisions.

**Relevance floor.** Both grounded QA and the agent now read `RELEVANCE_FLOOR`,
default **0.35**, against cosine similarity (`1 - Chroma distance`). This retains
the existing QA default rather than lowering safeguards; the agent previously used
a separate provisional 0.30. An environment override applies to both. These values
are screening parameters, not calibrated probabilities or proof of answerability.
Every document is filtered before evidence-based generation. No qualifying QA
evidence means a refusal before Claude; the agent also refuses a substantive final
answer when its search produced no usable evidence. Generic requests ask for clarification.

**Evaluation evidence still required.** No live threshold comparison has been
recorded in this work. The previous mocked scores 0.496 and 0.0784 test code paths,
not calibration. After indexing, run `python -m eval_thresholds --output
threshold_results.json`. It compares 0.25/0.30/0.35/0.40/0.45 on eight expected-source
questions and three unsupported questions. Review missed sources and false
admissions, then manually inspect answerability. Record the actual settings,
results and chosen trade-off before submission. Do not claim 0.35 is optimal.

**Chunking.** The eight documents are short, structured prose (31–47 lines each).
The current loader embeds each complete document, retaining headings and procedure
context. No AML chunking is implemented. Whole documents are a reasonable baseline
at this size; longer policies should be evaluated with section-aware chunks that
retain source IDs. Smaller chunks are not automatically better: they may lose
exceptions and increase retrieval/context cost.

**Worst wrong answer and controls.** A dangerous outcome is a confidently invented
reporting threshold or timing/intent claim leading an analyst to close an unresolved
alert. Transactions currently have no timestamps; prompts distinguish this from
alert creation dates and require missing evidence to be identified. Retrieved
citations must reference actual admitted documents; citation checks do not prove
semantic support for every assertion. Summary/triage are still model-generated,
so prompt compliance and factual accuracy require human review and live evaluation.
The agent exposes read-only knowledge/link tools, rejects unknown/malformed calls,
reports errors without raw provider data, and stops at four model turns by default.
Retrieved instructions cannot grant mutation capabilities. The limit bounds cost
and looping, but is a design default rather than an experimentally optimal value.

Actual closure uses a separate protected API requiring a reviewer credential,
active analyst ID and justification. Ordinary create/update cannot close alerts;
triage recommendations never mutate records. Closure records previous status,
reviewer ID, UTC timestamp and reason. A shared key is prototype authorisation,
not verified individual identity; audit and structured records are in memory.
Individual authentication, durable audit/records and stronger claim validation
remain production work. The default Haiku model is a small-model coursework choice
for interactive cost/latency; no comparative model benchmark is claimed.
