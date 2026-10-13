import re
from corpus import CORPUS_DOCUMENTS
from documents import DOCUMENTS
from eval_set import EVAL_SET, answerable
from eval_tools import contains_evidence, keyword_present, normalise


ALL_DOCS = {d["id"]: d for d in  DOCUMENTS + CORPUS_DOCUMENTS}

def section_containing(body:str, evidence: str) -> tuple[str, str]:
    """Return (heading, section text) for the section holding the evidence."""
    for part in re.split(r"(?m)^##", body):
        heading,__, text = part.partition("\n")
        if contains_evidence(text, evidence):
            return heading.strip(), text
    raise AssertionError(f"evidence not found in any section:{evidence}")


#test ids are unqiue in the eval_set


def test_eval_ids_are_unique():
    ids = [question["id"] for question in EVAL_SET]

    assert len(ids) == len(set(ids)), "Duplicate question IDs in EVAL_SET"

#test every evidence span is in its documents

def test_evidence_exists_in_source_document():
    for question in answerable():
        doc_id = question["doc_id"]

        assert doc_id in ALL_DOCS, f"Unknown document: {doc_id}"

        assert contains_evidence(
            ALL_DOCS[doc_id]["body"],
            question["evidence"],
        ), f"Evidence missing for {question['id']} in {doc_id}"


#test every evidence span appears exactly once in the whole corpus

def test_evidence_appears_exactly_once_in_corpus():
    for question in answerable():
        evidence = normalise(question["evidence"])

        occurrences = sum(
            normalise(doc["body"]).count(evidence)
            for doc in ALL_DOCS.values()
        )

        assert occurrences == 1, (
            f"{question['id']}: evidence appears {occurrences} times "
            "across the corpus; expected exactly 1"
        )




#test keywords matching in whole and word refusal
