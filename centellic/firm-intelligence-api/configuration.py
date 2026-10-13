"""Shared retrieval configuration; the default is a baseline, not calibrated truth."""
import os
import math

RELEVANCE_FLOOR = float(os.getenv("RELEVANCE_FLOOR", "0.35"))
if not math.isfinite(RELEVANCE_FLOOR) or not 0 <= RELEVANCE_FLOOR <= 1:
    raise ValueError("RELEVANCE_FLOOR must be between 0 and 1")
