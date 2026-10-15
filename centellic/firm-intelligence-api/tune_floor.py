"""
Sweep relevance floors for one or more chunking strategies and pick the best.
Builds the index + embeds questions ONCE per strategy, then re-scores each floor
in memory (no extra model calls beyond what each floor actually triggers).

Usage:
    python -m tune_floor sections_contextual
    python -m tune_floor sections_contextual sections_plain --floors 0.30 0.35 0.40 0.45 0.50 0.55 0.60
"""

import argparse
import json
from pathlib import Path

import chunk_index
from eval_answers import run
from eval_set import EVAL_SET


DEFAULT_FLOORS = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65]


def score(r: dict) -> tuple:
    # rank by combined accuracy, then fewer false refusals, then fewer wrong
    combined = r["answer_accuracy"] + r["refusal_accuracy"]
    return (combined, -len(r["false_refusals"]), -len(r["wrong_or_unrefused"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("strategies", nargs="+")
    parser.add_argument("--floors", type=float, nargs="+", default=DEFAULT_FLOORS)
    args = parser.parse_args()

    for strategy in args.strategies:
        chunk_index.build(strategy)
    vectors, _ = chunk_index.embed_batched(
        [q["question"] for q in EVAL_SET], input_type="query"
    )

    all_results: dict = {}
    best: tuple = ((-1.0, 0, 0), None, None, None)  # (score_key, strategy, floor, result)

    for strategy in args.strategies:
        print(f"\n=== {strategy} ===")
        print(f"{'floor':>6}{'answers':>10}{'refusals':>10}{'calls':>7}{'avg tok':>10}  false_refusals / wrong")
        all_results[strategy] = {}
        for floor in args.floors:
            r = run(strategy, vectors, floor)
            all_results[strategy][f"{floor:.2f}"] = r
            print(
                f"{floor:>6.2f}{r['answer_accuracy']:>10.2f}{r['refusal_accuracy']:>10.2f}"
                f"{r['model_calls']:>7}{r['avg_input_tokens']:>10}  "
                f"fr=[{', '.join(r['false_refusals']) or '-'}]  "
                f"wr=[{', '.join(r['wrong_or_unrefused']) or '-'}]"
            )
            key = score(r)
            if key > best[0]:
                best = (key, strategy, floor, r)

    _, s, f, r = best
    print("\n=== BEST ===")
    print(f"strategy = {s}  floor = {f:.2f}")
    print(f"answer_accuracy = {r['answer_accuracy']:.2f}  refusal_accuracy = {r['refusal_accuracy']:.2f}")
    print(f"model_calls = {r['model_calls']}  avg_input_tokens = {r['avg_input_tokens']}")
    print(f"false_refusals: {', '.join(r['false_refusals']) or 'none'}")
    print(f"wrong_or_unrefused: {', '.join(r['wrong_or_unrefused']) or 'none'}")

    Path("eval_results").mkdir(exist_ok=True)
    Path("eval_results/floor_sweep.json").write_text(
        json.dumps(
            {
                "floors": args.floors,
                "results": all_results,
                "best": {"strategy": s, "floor": f, **r},
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()