"""Opt-in LIVE retrieval experiment: Voyage calls, persistent Chroma, no Claude.

Run only after indexing. Results measure expected-source retrieval and admission,
not semantic answer correctness. No historical measurements are fabricated.
"""
import argparse
import json
from pathlib import Path

from knowledge_store import index_is_built, search

CASES = [
    ("How should analysts handle a partial sanctions name match?", "doc-001"),
    ("When should multiple alerts be grouped into one investigation case?", "doc-002"),
    ("What customer profile information should be compared with unusual payments?", "doc-003"),
    ("What steps are required before recommending an alert outcome?", "doc-004"),
    ("What information belongs in a suspicious activity reporting narrative?", "doc-005"),
    ("What evidence supports recommending closure of a false positive?", "doc-006"),
    ("What indicators suggest a potential money mule account?", "doc-007"),
    ("How should three accounts paying one counterparty be investigated for possible structuring?", "doc-008"),
    ("What is the holiday policy for a trip to Mars?", None),
    ("What mortgage interest rate should I choose?", None),
    ("What exact statutory cash reporting threshold applies in every jurisdiction?", None),
]


def evaluate(ranked, floors=(0.25, 0.30, 0.35, 0.40, 0.45)):
    results = {}
    for floor in floors:
        successes = false_admissions = 0
        for (_, expected), hits in zip(CASES, ranked):
            admitted = [h for h in hits if h["score"] >= floor]
            if expected is None:
                false_admissions += bool(admitted)
            else:
                successes += any(h["id"] == expected for h in admitted)
        results[str(floor)] = {
            "expected_source_hits_at_3": successes,
            "answerable_cases": 8,
            "unsupported_cases_admitted": false_admissions,
            "unsupported_cases": 3,
        }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="Optional JSON results path")
    args = parser.parse_args()
    if not index_is_built():
        raise SystemExit("Build the index with POST /knowledge/index first.")
    ranked = [search(question, top_k=3) for question, _ in CASES]
    report = {"note": "Live retrieval scores; not answer correctness or calibrated probabilities.",
              "thresholds": evaluate(ranked),
              "cases": [{"question": q, "expected_document": expected, "hits": hits}
                        for (q, expected), hits in zip(CASES, ranked)]}
    text = json.dumps(report, indent=2)
    print(text)
    if args.output:
        args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
