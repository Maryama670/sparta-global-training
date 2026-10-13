""" How retrieved hits become the text the model reads failure: lost in the middle
"""

#hits order for context is intended to arrange retrieved docuemnrs before they're sent to claude
#Original:  1, 2, 3, 4, 5
#Reordered: 1, 3, 5, 4, 2

def order_for_context(hits: list[dict]) ->list[dict]:

    ranked = sorted(hits, key=lambda h: h['score'], reverse=True)
    """ Best hit first second best last weakest in the middle
    Ranked [a, b, c, d, e] -> [a, c, e, d, b]
    """
    front = ranked[::2] # a c e
    back = ranked[1::2] # b d
    return front +back[::-1] # a c e d b


def build_context(hits: list[dict]) -> str:
    """The exact text block the model sees, one labelled section per hit."""
    return "\n\n".join(f"[{h['id']}] {h['title']}\n{h['text']}" for h in order_for_context(hits))

#whats failure mode ?