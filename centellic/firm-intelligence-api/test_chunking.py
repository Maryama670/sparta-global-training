"""Check that chunking preserves text and adds context only when requested."""

# Load pytest so tests can check for expected errors.
import pytest

# Load the chunking functions being tested.
import chunking
# Load the newer, longer documents.
from corpus import CORPUS_DOCUMENTS
# Load the original documents.
from documents import DOCUMENTS

# Select document 105 as an example for the word-based tests.
DOC = next(d for d in CORPUS_DOCUMENTS if d["id"] == "doc-105")
# Combine both collections into one document list.
ALL_DOCS = DOCUMENTS + CORPUS_DOCUMENTS


# Check that splitting without overlap preserves every word in order.
def test_fixed_chunks_without_overlap_lose_no_words():
    # Split the example into 100-word chunks with no repeated words.
    chunks = chunking.fixed_words(DOC, size=100, overlap=0)
    # Join the chunk texts, then turn the combined text into a list of words.
    rebuilt = " ".join(c["text"] for c in chunks).split()
    # Check that this word list exactly matches the original word list.
    assert rebuilt == DOC["body"].split()


# Check that neighbouring chunks share exactly the intended 25 words.
def test_overlap_repeats_exactly_the_overlap_words():
    # Create 100-word chunks that repeat 25 words between neighbours.
    chunks = chunking.fixed_words(DOC, size=100, overlap=25)
    # Make sure there are at least two chunks to compare.
    assert len(chunks) > 1
    # Pair each chunk with the next one; chunks[1:] starts at the second chunk.
    for first, second in zip(chunks, chunks[1:]):
        # Compare the last 25 words of the first with the first 25 of the next.
        assert first["text"].split()[-25:] == second["text"].split()[:25]


# Check that an overlap equal to the chunk size is rejected.
def test_overlap_must_be_smaller_than_size():
    # Expect the following call to raise ValueError; otherwise this test fails.
    with pytest.raises(ValueError):
        # These settings leave zero words of forward movement.
        chunking.fixed_words(DOC, size=100, overlap=100)


# Check that sentence packing keeps whole sentences, even above the word limit.
def test_sentence_packing_never_cuts_a_sentence():
    # Create a document with two short sentences and one six-word sentence.
    doc = {"id": "test-doc", "title": "Hiring Report", "body": "The firm grew. Pay rose. Six new partners joined last year."}
    # Use a five-word limit: the first two sentences fit together exactly.
    chunks = chunking.sentence_packed(doc, max_words=5)
    # Collect only the text from each returned chunk dictionary.
    texts = [chunk["text"] for chunk in chunks]
    # Check exact contents: the long sentence must stay whole in its own chunk.
    assert texts == ["The firm grew. Pay rose.", "Six new partners joined last year."]


# Check that contextual chunks include the document title and section heading.
def test_contextual_sections_carry_little_headings():
    # Create one section; \n separates its heading from its body text.
    doc = {"id": "test-doc", "title": "Hiring Report", "body": "## London\nFive partners joined."}
    # Split by section with the title-and-heading prefix switched on.
    chunks = chunking.by_section(doc, contextual=True)
    # Check that the small section produced exactly one chunk.
    assert len(chunks) == 1
    # Check that its text includes the title, heading, newline, and sentence.
    assert chunks[0]["text"] == "Hiring Report > London\nFive partners joined."


# Check plain section text; despite this test's name, headings are not prefixed.
def test_plain_sections_carry_headings():
    # Use the same small document so we can compare with the contextual case.
    doc = {"id": "test-doc", "title": "Hiring Report", "body": "## London\nFive partners joined."}
    # Split by section with the prefix switched off.
    chunks = chunking.by_section(doc, contextual=False)
    # Check that this section still produced exactly one chunk.
    assert len(chunks) == 1
    # Check that the text is just the sentence, without a title or heading prefix.
    assert chunks[0]["text"] == "Five partners joined."
