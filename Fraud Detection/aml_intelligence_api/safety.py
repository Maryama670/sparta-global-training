"""Small shared evidence guards; citation validity is not semantic truth."""

import re

INSUFFICIENT_EVIDENCE = "I do not have sufficient relevant evidence to answer this question."
CLARIFICATION = "Please clarify the alert ID, transaction pattern or AML procedure you want to investigate."


def needs_clarification(question: str) -> bool:
    """Catch explicit empty/generic requests, not every form of ambiguity."""
    words = re.findall(r"\w+", question.lower())
    generic = {
        "help", "help me", "what should i do", "what do i do", "investigate",
        "is this suspicious", "close it", "what about this", "tell me more",
    }
    return not words or " ".join(words) in generic


def citation_ids(answer: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\[(doc-[^\]\s]+)\]", answer)))


def valid_citations(answer: str, allowed_ids: set[str]) -> bool:
    cited = citation_ids(answer)
    return bool(cited) and set(cited).issubset(allowed_ids)
