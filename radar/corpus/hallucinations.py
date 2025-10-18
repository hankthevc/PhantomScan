"""Known hallucination detection for package names."""

import re
from pathlib import Path
from typing import Pattern

import yaml


_HALLUCINATIONS_CACHE: tuple[set[str], list[Pattern[str]]] | None = None


def load_hallucinations(corpus_file: str | Path | None = None) -> tuple[set[str], list[Pattern[str]]]:
    """Load known hallucination patterns from corpus file.

    Args:
        corpus_file: Path to hallucinations.yml (default: config/hallucinations.yml)

    Returns:
        Tuple of (exact_matches, regex_patterns)
    """
    global _HALLUCINATIONS_CACHE

    if _HALLUCINATIONS_CACHE is not None:
        return _HALLUCINATIONS_CACHE

    if corpus_file is None:
        corpus_file = Path("config/hallucinations.yml")
    else:
        corpus_file = Path(corpus_file)

    if not corpus_file.exists():
        # Return empty sets if file doesn't exist (graceful degradation)
        _HALLUCINATIONS_CACHE = (set(), [])
        return _HALLUCINATIONS_CACHE

    with open(corpus_file) as f:
        data = yaml.safe_load(f)

    # Load exact matches (lowercase for case-insensitive matching)
    exact_matches = set()
    for name in data.get("exact", []):
        exact_matches.add(name.lower())

    # Compile regex patterns
    regex_patterns = []
    for pattern_str in data.get("patterns", []):
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            regex_patterns.append(pattern)
        except re.error as e:
            # Skip invalid patterns with a warning
            import warnings
            warnings.warn(f"Invalid regex pattern '{pattern_str}': {e}")

    _HALLUCINATIONS_CACHE = (exact_matches, regex_patterns)
    return _HALLUCINATIONS_CACHE


def is_known_hallucination(name: str, corpus_file: str | Path | None = None) -> tuple[bool, str]:
    """Check if a package name is a known hallucination.

    Args:
        name: Package name to check
        corpus_file: Optional path to hallucinations corpus

    Returns:
        Tuple of (is_hallucination, reason)
    """
    exact_matches, regex_patterns = load_hallucinations(corpus_file)

    name_lower = name.lower()

    # Check exact matches
    if name_lower in exact_matches:
        return True, f"Known hallucinated package name: '{name}'"

    # Check regex patterns
    for pattern in regex_patterns:
        if pattern.search(name):
            return True, f"Matches hallucination pattern: {pattern.pattern}"

    return False, ""
