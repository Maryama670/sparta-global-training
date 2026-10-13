# Testing the model for hallucination to see if it can detect traps.
# This will not be a feature in the final product.

"""
Same evidence, same questions, two system prompts.

Goal:
Compare what happens when we use:
1. A loose prompt
2. A grounded prompt
"""

import grounding
import llm
from corpus import CORPUS_DOCUMENTS


LOOSE_PROMPT = (
    "You are a helpful legal market analyst. "
    "Answer the question as fully and helpfully as you can. "
    "Cite the document id in square brackets where you use it."
)


QUESTIONS = [
    "Who is the managing partner of Harding & Voss, and how long have they held the role?",
    "How does Harding & Voss's profitability compare with the Magic Circle firms?",
]


def main() -> None:
    doc = next(
        d for d in CORPUS_DOCUMENTS
        if d["id"] == "doc-101"
    )

    context = f"[{doc['id']}] {doc['title']}\n{doc['body']}"

    # Two questions × two prompts = four model calls
    #
    # Q1 -> loose
    # Q1 -> grounded
    # Q2 -> loose
    # Q2 -> grounded

    for question in QUESTIONS:
        print("=" * 50)
        print("QUESTION:", question)

        for name, prompt in [
            ("loose", LOOSE_PROMPT),
            ("grounded", llm.GROUNDED_SYSTEM_PROMPT),
        ]:
            result = llm.answer_from_context(
                question,
                context,
                system=prompt,
            )

            report = grounding.check_citations(
                result["answer"],
                [doc["id"]],
            )

            print(f"\n--- {name} prompt ---")
            print(result["answer"])

            print("\nCitation check:")
            print("Refusal:", report["refusal"])
            print("Passed:", report["passed"])

            for sentence in report["uncited_sentences"]:
                print(f"Uncited: {sentence}")


if __name__ == "__main__":
    main()