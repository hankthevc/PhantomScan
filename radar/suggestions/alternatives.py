"""Suggest safer alternative packages for near-miss names."""

from rapidfuzz import fuzz
from typing import Any


def suggest_alternatives(
    name: str,
    ecosystem: str,
    canonical_list: list[str],
    threshold: int = 92,
    max_results: int = 5,
) -> list[tuple[str, float]]:
    """Suggest alternative packages that are close matches to the given name.
    
    This helps users who might have mistyped or been deceived by a typosquat
    to find the legitimate package they were looking for.
    
    Args:
        name: Package name to find alternatives for
        ecosystem: Package ecosystem ("pypi" or "npm")
        canonical_list: List of canonical/legitimate package names
        threshold: Minimum similarity threshold (0-100, Jaro-Winkler equivalent)
        max_results: Maximum number of alternatives to return
        
    Returns:
        List of (alternative_name, similarity_score) tuples, sorted by similarity
    """
    if not name or not canonical_list:
        return []
    
    alternatives = []
    name_lower = name.lower()
    
    for canonical in canonical_list:
        canonical_lower = canonical.lower()
        
        # Skip exact matches
        if name_lower == canonical_lower:
            continue
        
        # Calculate similarity using Jaro-Winkler (which favors prefix matches)
        jaro_similarity = fuzz.ratio(name_lower, canonical_lower)
        
        # Also calculate Levenshtein distance for near-misses
        levenshtein_similarity = fuzz.ratio(name_lower, canonical_lower)
        
        # Use the higher of the two scores
        similarity = max(jaro_similarity, levenshtein_similarity)
        
        # Only include if above threshold
        if similarity >= threshold:
            alternatives.append((canonical, similarity))
    
    # Sort by similarity (descending)
    alternatives.sort(key=lambda x: x[1], reverse=True)
    
    return alternatives[:max_results]


def suggest_from_policy(
    name: str,
    ecosystem: str,
    policy: dict[str, Any],
) -> list[tuple[str, float]]:
    """Suggest alternatives using canonical list from policy.
    
    Args:
        name: Package name
        ecosystem: Package ecosystem ("pypi" or "npm")
        policy: Policy configuration dict
        
    Returns:
        List of (alternative_name, similarity_score) tuples
    """
    heuristics = policy.get("heuristics", {})
    canonical_packages = heuristics.get("canonical_packages", {})
    
    ecosystem_key = "pypi" if ecosystem.lower() == "pypi" else "npm"
    canonical_list = canonical_packages.get(ecosystem_key, [])
    
    # Use fuzzy threshold from policy
    threshold = 100 - heuristics.get("fuzzy_threshold", 15)
    
    return suggest_alternatives(name, ecosystem, canonical_list, threshold=threshold)


def format_alternatives(alternatives: list[tuple[str, float]]) -> str:
    """Format alternatives list as a human-readable string.
    
    Args:
        alternatives: List of (name, similarity) tuples
        
    Returns:
        Formatted string
    """
    if not alternatives:
        return "No similar canonical packages found"
    
    lines = ["Did you mean:"]
    for alt_name, similarity in alternatives:
        lines.append(f"  • {alt_name} ({similarity:.0f}% similar)")
    
    return "\n".join(lines)


def compute_edit_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings.
    
    This is a fallback in case RapidFuzz ratio isn't granular enough.
    
    Args:
        s1: First string
        s2: Second string
        
    Returns:
        Edit distance (number of single-character edits)
    """
    # Using RapidFuzz's distance module
    from rapidfuzz import distance
    
    return distance.Levenshtein.distance(s1.lower(), s2.lower())
