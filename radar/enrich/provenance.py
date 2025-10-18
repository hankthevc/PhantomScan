"""Provenance indicator enrichment."""

from typing import Any


def npm_provenance_indicator(packument_json: dict[str, Any]) -> float:
    """Check for npm provenance signatures.

    npm provenance provides cryptographic proof of package origin.

    Args:
        packument_json: npm packument (full package document)

    Returns:
        Risk score: 0.0 if provenance present, 1.0 if absent
    """
    if not packument_json:
        return 1.0

    # Check for provenance in latest version
    dist_tags = packument_json.get("dist-tags", {})
    latest_version = dist_tags.get("latest")

    if not latest_version:
        return 1.0

    versions = packument_json.get("versions", {})
    latest_data = versions.get(latest_version, {})

    # Check for npm provenance fields
    # npm provenance adds 'attestations' or '_npmProvenance' fields
    dist = latest_data.get("dist", {})

    # Check for provenance signatures
    if "attestations" in dist:
        return 0.0  # Has provenance

    if "signatures" in dist:
        sigs = dist.get("signatures", [])
        # Check if any signature has provenance keyid
        for sig in sigs:
            if isinstance(sig, dict) and "keyid" in sig:
                # Presence of signature suggests provenance
                return 0.2  # Low risk

    # Check for deprecated _npmProvenance field (older format)
    if "_npmProvenance" in latest_data:
        return 0.0

    # No provenance indicators found
    return 1.0


def pypi_provenance_indicator(info_json: dict[str, Any]) -> float:
    """Check for PyPI provenance indicators.

    Note: PyPI provenance (PEP 740) is still in development.
    This is a placeholder that always returns 1.0 (no provenance).

    Args:
        info_json: PyPI JSON API response

    Returns:
        Risk score: Currently always 1.0 (not yet implemented)
    """
    # Placeholder: PyPI provenance not yet widely adopted
    # When PEP 740 is implemented, check for provenance fields
    # For now, always return 1.0 (neutral - not penalizing lack of provenance)
    return 1.0
