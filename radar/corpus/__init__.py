"""Corpus management for PhantomScan."""

from radar.corpus.hallucinations import (
    is_known_hallucination,
    load_hallucinations,
)

__all__ = [
    "is_known_hallucination",
    "load_hallucinations",
]
