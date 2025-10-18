"""Known-hallucination corpus matching."""

import re
from pathlib import Path
from typing import Pattern

import yaml


_EXACT_MATCHES: set[str] = set()
_REGEX_PATTERNS: list[Pattern[str]] = []
_LOADED = False


def load_hallucinations(config_path: str | Path | None = None) -> tuple[set[str], list[Pattern[str]]]:
    """Load hallucination corpus from YAML file.
    
    Args:
        config_path: Path to hallucinations.yml. If None, uses default from policy.
        
    Returns:
        Tuple of (exact_matches set, regex_patterns list)
    """
    global _EXACT_MATCHES, _REGEX_PATTERNS, _LOADED
    
    if _LOADED and config_path is None:
        return _EXACT_MATCHES, _REGEX_PATTERNS
    
    if config_path is None:
        # Load from default location
        config_path = Path("config/hallucinations.yml")
    else:
        config_path = Path(config_path)
    
    if not config_path.exists():
        # Return empty sets if file doesn't exist (graceful degradation)
        return set(), []
    
    with open(config_path, "r") as f:
        data = yaml.safe_load(f) or {}
    
    # Load exact matches (case-insensitive)
    exact = set()
    for name in data.get("exact_matches", []):
        if isinstance(name, str):
            exact.add(name.lower())
    
    # Compile regex patterns
    patterns = []
    for pattern_str in data.get("regex_patterns", []):
        if isinstance(pattern_str, str):
            try:
                patterns.append(re.compile(pattern_str, re.IGNORECASE))
            except re.error:
                # Skip invalid regex patterns
                pass
    
    _EXACT_MATCHES = exact
    _REGEX_PATTERNS = patterns
    _LOADED = True
    
    return exact, patterns


def is_known_hallucination(name: str, config_path: str | Path | None = None) -> tuple[bool, str]:
    """Check if a package name is a known hallucination.
    
    Args:
        name: Package name to check
        config_path: Optional path to hallucinations.yml
        
    Returns:
        Tuple of (is_hallucination, reason)
    """
    if not name:
        return False, ""
    
    exact_matches, regex_patterns = load_hallucinations(config_path)
    name_lower = name.lower()
    
    # Check exact match
    if name_lower in exact_matches:
        return True, f"Known hallucinated name: {name}"
    
    # Check regex patterns
    for pattern in regex_patterns:
        if pattern.match(name_lower):
            return True, f"Matches hallucination pattern: {pattern.pattern}"
    
    return False, ""


def reload_hallucinations(config_path: str | Path | None = None) -> None:
    """Force reload of hallucination corpus.
    
    Args:
        config_path: Path to hallucinations.yml
    """
    global _LOADED
    _LOADED = False
    load_hallucinations(config_path)
