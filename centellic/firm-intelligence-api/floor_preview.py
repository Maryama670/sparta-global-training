import chunk_index
from eval_set import EVAL_SET

STRATEGY = "section_contextual"


def main() -> None:
    vectors, _ = chunk_index.embed_batched([q["question"] for q in EVAL_SET], input_type="query")
    ranked = chunk_index.search_with_vectors(STRATEGY, vectors, k=3)

    if len(ranked) != len(EVAL_SET) or any(not hits for hits in ranked):
        raise ValueError("Each question must have a non-empty ranked result list")
    answerable_count = sum(bool(q["doc_id"]) for q in EVAL_SET)
    unanswerable_count = len(EVAL_SET) - answerable_count
    rows = sorted((hits[0]["score"], q["id"], q["kind"], bool(q["doc_id"])) for q, hits in zip(EVAL_SET, ranked))

    print("best-hit score per question, lowest first")
    for score, qid, kind, answerable in rows:
        print(f"  {score:.3f}  {qid}  {kind:<18} {'answerable' if answerable else 'UNANSWERABLE'}")

    print("\nwhat each floor refuses at the gate, before the model is ever called")
    for floor in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65):
        bad = sum(1 for s, _, _, a in rows if a and s < floor)
        good = sum(1 for s, _, _, a in rows if not a and s < floor)
        print(f"  floor {floor:.2f}: refuses {bad:>2} of {answerable_count} answerable (bad)   {good} of {unanswerable_count} unanswerable (good)")


if __name__ == "__main__":
    main()
