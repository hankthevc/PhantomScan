"""Suggest safer canonical alternatives for suspicious package names."""

from rapidfuzz import fuzz

from radar.types import Ecosystem


def suggest_alternatives(
    name: str, ecosystem: Ecosystem | str, canonical_list: list[str], threshold: int = 92
) -> list[tuple[str, float]]:
    """Suggest safer alternative packages based on fuzzy matching.

    Args:
        name: Suspicious package name
        ecosystem: Package ecosystem
        canonical_list: List of canonical/trusted package names
        threshold: Jaro-Winkler similarity threshold (0-100, default 92)

    Returns:
        List of (alternative_name, similarity_score) tuples, sorted by similarity
    """
    if not name or not canonical_list:
        return []

    # Normalize ecosystem
    if isinstance(ecosystem, Ecosystem):
        ecosystem_str = ecosystem.value
    else:
        ecosystem_str = str(ecosystem).lower()

    alternatives = []
    name_lower = name.lower()

    for canonical in canonical_list:
        canonical_lower = canonical.lower()

        # Skip if exact match (shouldn't happen for suspicious packages)
        if name_lower == canonical_lower:
            continue

        # Compute Jaro-Winkler similarity (0-100)
        jw_score = fuzz.WRatio(name_lower, canonical_lower)

        if jw_score >= threshold:
            alternatives.append((canonical, jw_score))

    # Sort by similarity descending
    alternatives.sort(key=lambda x: x[1], reverse=True)

    # Limit to top 5 alternatives
    return alternatives[:5]


def get_distance_description(similarity: float) -> str:
    """Get human-readable description of similarity.

    Args:
        similarity: Similarity score (0-100)

    Returns:
        Description string
    """
    if similarity >= 95:
        return "very similar"
    elif similarity >= 90:
        return "similar"
    elif similarity >= 85:
        return "somewhat similar"
    else:
        return "moderately similar"
