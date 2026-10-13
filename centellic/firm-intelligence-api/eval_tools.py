"""small, pure helpers for scoring.no network and no model"""


import re

from grounding import is_refusal, normalise # line definition of refusal

def contains_evidence(chunk_text:str, evidence: str) -> bool:
    """ True if chunk holds the whole evidence span. Line breaks never break a match"""
    return normalise (evidence) in normalise (chunk_text)

#alternative_matches
def alternative_matches(answer:str, alternatives:list[str]) -> bool:
    """True when at least one alternative matches the answer."""
    return any(_alternative_matches(answer, alternative) for alternative in alternatives)


def _alternative_matches(answer: str, alternative: str) -> bool:
    prefix = alternative.endswith("*")
    core = re.escape(normalise(alternative[:-1] if prefix else alternative))
    ending = "" if prefix else r"(?![a-z0-9])"
    return re.search(rf"(?<![a-z0-9]){core}{ending}", normalise(answer)) is not None

#above turns formats, unqiue keys to be fixed or returned

#keywords_present
#what the keywords list looks like
#question                                    keywords                     meaning
#q11 (offshore wind capacity)                ["4.2"]                      Must mention 4.2
#q14 (okonkwo bell offices)                  ["Lagos", "Nairobi"]         Must mention both Lagos and Nairobi

def keyword_present(answer: str | None, keywords:list[str]) ->bool:
    """ True only for a non-refusal answer that contains every keyword group"""

    if is_refusal(answer):
        return False
    if answer is None:
        return False
    return all(
        any(_alternative_matches(answer, alt) for alt in group.split("|")) for group in keywords

    )
#answer                                #result
#offices in lagos and nairobi           TRUE
#An office in lagos                     False
#An office in nairobi                   False
