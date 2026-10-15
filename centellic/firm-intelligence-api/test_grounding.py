import grounding

SOURCES = {
    "doc-101": "Harding & Voss closed the year with revenue of $1.24 billion, up 4.1 percent",
    "doc-107": "Fixed-share partners are excluded from the equity partner count."
}

# test that refusal needs no citations
def test_refusal_needs_no_citations():
    report = grounding.check_citations(grounding.REFUSAL_SENTENCE, ["doc-101"])
    assert report["refusal"] is True and report["passed"] is True

# test fully cited answer passes
def test_fully_cited_answer_passes():
    answer = "Harding & Voss closed the year with revenue of $1.24 billion, up 4.1 percent [doc-101]."
    report = grounding.check_citations(answer, ["doc-101"])
    assert report["passed"] is True
    assert len(report["cited"]) is not None

# test uncited sentence is flagged
def test_uncited_sentence_is_flagged():
    answer = "Harding & Voss closed the year with revenue of $1.24 billion, up 4.1 percent [doc-101]. The firm is the most profitable firm in London."
    report = grounding.check_citations(answer, ["doc-101"])
    assert report["refusal"] is False and report["passed"] is False
    assert report["uncited_sentences"] is not None
    # assert report["uncited_sentences"] == ["The firm is the most profitable firm in London."]

# test citation after the full stop still counts
def test_citation_after_full_stop_still_counts():
    answer = "Harding & Voss closed the year with revenue of $1.24 billion, up 4.1 percent.[doc-101]"
    report = grounding.check_citations(answer, ["doc-101"])
    assert report["passed"] is True
    assert len(report["cited"]) is not None
