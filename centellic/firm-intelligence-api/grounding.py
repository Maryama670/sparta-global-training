"""Check citation structure, not whether source text proves a claim."""

import re
from typing import TypedDict

REFUSAL_SENTENCE = "The provided documents do not answer the question."
CITATION = re.compile(r"\[(doc-\d{3})\]")


class CitationCheck(TypedDict):
    refusal: bool
    cited: list[str]
    invalid: list[str]
    uncited_sentences: list[str]
    passed: bool


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def is_refusal(answer: str | None) -> bool:
    return answer is None or normalise(answer) == normalise(REFUSAL_SENTENCE)


def split_sentences(text: str) -> list[str]:
    """Keep citations after a full stop attached to the preceding sentence."""
    pieces: list[str] = []
    for line in text.splitlines():
        line = line.strip(" -*\t")
        if line:
            pieces.extend(p for p in re.split(r"(?<=[.!?])\s+", line) if p)

    sentences: list[str] = []
    for piece in pieces:
        trailing = re.match(r"^(?:\[doc-\d{3}\]\s*)+", piece)
        if sentences and trailing:
            sentences[-1] = f"{sentences[-1]} {trailing.group().strip()}"
            piece = piece[trailing.end() :].strip(" .")
        if piece:
            sentences.append(piece)
    return sentences


def citations_in(text: str) -> list[str]:
    return CITATION.findall(text)


def check_citations(answer: str | None, source_ids: list[str]) -> CitationCheck:
    """Flag uncited sentences and citations to sources we did not supply."""
    if answer is None or is_refusal(answer):
        return {
            "refusal": True,
            "cited": [],
            "invalid": [],
            "uncited_sentences": [],
            "passed": True,
        }

    sentences = split_sentences(answer)
    cited = sorted(set(citations_in(answer)))
    mentioned = sorted(set(re.findall(r"\[(doc-[^\]\s]+)\]", answer)))
    invalid = [doc_id for doc_id in mentioned if doc_id not in source_ids]
    # Retain the lesson's heuristic: skip sentences shorter than three words.
    uncited = [
        sentence
        for sentence in sentences
        if not CITATION.search(sentence) and len(sentence.split()) >= 3
    ]
    return {
        "refusal": False,
        "cited": cited,
        "invalid": invalid,
        "uncited_sentences": uncited,
        "passed": bool(sentences) and bool(cited) and not invalid and not uncited,
    }
