"""
Chunking strategies
Every strategu takes a documnet and returns a list of chunks
A chunk is  adict:

-id "<doc id>#<two-digit-number>, kept stable for the same input
-doc_id the parent document used for citations
-title the patent documents title
-text exactly what gets embedded and what model will read


"""
import re
from collections.abc import Iterable
from typing import Any
import corpus
import documents

def _chunk(doc: dict, number: int, text: str) -> dict:
    # 2 -> 02 # why is this the case?
    # with padding ['doc-105#01', 'doc-105#02', 'doc-105#10']
    # with padding ['doc-105#01', 'doc-105#010', 'doc-105#2']

    return {"id": f"{doc["id"]}#{number:02d}", "doc_id": doc["id"], "title": doc["title"], "text": text}

# below are repeatable steps that we will include into our steps

def split_sentences(text: str) -> list[str]:

    """sentences, with each '## Heading' line kept as a unit of its own"""
    units = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('##'):  # how the headings are denoted
            units.append(line)
        else:
            units.extend(s for s in re.split(r"(?<=[.!?])\s+", line) if s)
    return units


# exceed max words

def pack(units: list[str], max_words: int) -> list[str]:
    """Group whole units without splitting a sentence in half."""
    if max_words < 1:
        raise ValueError("max_words must be at least 1")
    # groups holds finished chunks; current holds the units being collected.
    groups, current, count = [], [], 0
    for unit in units:
        n = len(unit.split())
        if current and count + n > max_words:
            groups.append(" ".join(current))
            current, count = [], 0
        current.append(unit)
        count += n
    if current:
        groups.append(" ".join(current))
    return groups


# --------------------------CHUNKING STRATEGIES-----------------------

# Whole document
def whole_document(doc: dict) -> list[dict]:
    """ baseline...what our project has done until now """

    return [_chunk(doc, 0, doc["body"].strip())]
# can change 0 to 25 overlap this covers another strategy
# fixed_words
def fixed_words(doc: dict, size: int = 100, overlap: int = 0) -> list[dict]:
    """Every size words, regardless of sentence or section boundaries."""
    if not 0 <= overlap < size:
        raise ValueError("overlap must be at least 0 and smaller than size")
    words = doc["body"].split()
    step = size - overlap
    chunks = []
    for number, start in enumerate(range(0, len(words), step)):
        chunks.append(_chunk(doc, number, " ".join(words[start : start + size])))
        if start + size >= len(words):
            break
    return chunks


# Challenge - build the next chunking strategy
# sentenced_packed - Whole sentences only, packed up to max_words. Never cuts a sentence in half.

# FUNCTION sentence_packed(document, max_words):

#     Split the document's body into sentences and headings
#     using split_sentences()

#     Group those units into text chunks using pack():
#         Keep whole sentences together
#         Start a new chunk when adding the next sentence
#         would exceed max_words

#     Create an empty results list

#     FOR each text chunk, numbered from 0:
#         Use _chunk(document, number, text)
#         Add the resulting chunk record to results

#     RETURN results
# Sentences 1–4  → doc-105#00 #this is one chunk#

def sentence_packed(doc: dict, max_words: int = 100) -> list[dict]:
    units = split_sentences(doc["body"])
    texts = pack(units, max_words)


    chunks = []
    for number, text in enumerate(texts):
        chunks.append(_chunk(doc, number, text))

    return chunks


def by_section(doc: dict, max_words: int = 150, contextual: bool = True) -> list[dict]:
    """Pack sentences within sections; optionally prefix title and heading."""
    chunks, number = [], 0
    # Capture headings so introductory text and heading-free bodies are retained.
    parts = re.split(r"(?m)^##[ \t]+([^\n]*)\n?", doc["body"])
    sections = [("", parts[0])]
    sections.extend(zip(parts[1::2], parts[2::2]))
    for heading, text in sections:
        heading, text = heading.strip(), text.strip()
        if not text:
            continue
        for piece in pack(split_sentences(text), max_words):
            if contextual:
                prefix = f"{doc['title']} > {heading}\n" if heading else f"{doc['title']}\n"
                piece = prefix + piece
            chunks.append(_chunk(doc, number, piece))
            number += 1
    return chunks


STRATEGIES = {
    "whole_document": whole_document,
    "fixed_100": lambda d: fixed_words(d, size=100, overlap=0),
    "fixed_overlap_25": lambda d: fixed_words(d, size=100, overlap=25),
    "sentences_100": lambda d: sentence_packed(d, max_words=100),
    "sections_plain": lambda d: by_section(d, max_words=150, contextual=False),
    "section_contextual": lambda d: by_section(d, max_words=150, contextual=True),
}


def chunk_corpus(docs: list[dict], strategy: str) -> list[dict]:
    return [chunk for doc in docs for chunk in STRATEGIES[strategy](doc)]


# Run this example only when executing this file, not when importing it.
if __name__ == "__main__":
    # Import chunking helpers from this file, plus the two document modules.


    # Combine old and new docs into one list.
    all_docs = documents.DOCUMENTS + corpus.CORPUS_DOCUMENTS

    # Loop through strategies and call chunk_corpus for each one.
    for strategy in STRATEGIES:
        chunks = chunk_corpus(all_docs, strategy)
        print(f"{strategy}: {len(all_docs)} documents -> {len(chunks)} chunks")
