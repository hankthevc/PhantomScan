"""Provenance indicators for npm and PyPI packages."""

from typing import Any


def npm_provenance_indicator(packument_json: dict[str, Any]) -> float:
    """Check for npm provenance/attestation indicators.
    
    npm packages can include provenance attestations that verify the
    package was built from a specific GitHub Actions workflow.
    
    Args:
        packument_json: Full packument JSON from npm registry
        
    Returns:
        Risk score: 0.0 if provenance present, 1.0 if absent
    """
    if not packument_json:
        return 1.0
    
    # Check latest version for provenance
    dist_tags = packument_json.get("dist-tags", {})
    latest_version = dist_tags.get("latest")
    
    if not latest_version:
        return 1.0
    
    # Get version metadata
    versions = packument_json.get("versions", {})
    latest_data = versions.get(latest_version, {})
    
    # Check for npm provenance/attestations
    dist = latest_data.get("dist", {})
    
    # Look for provenance-related fields
    # npm provenance includes "attestations" and "signatures" fields
    if "attestations" in dist:
        return 0.0
    
    if "signatures" in dist:
        sigs = dist.get("signatures", [])
        if sigs:
            return 0.0
    
    # Check for GitHub Actions provenance (recent npm feature)
    if "npm-signature" in dist:
        return 0.2  # Some provenance, but older format
    
    # No provenance found
    return 1.0


def pypi_provenance_indicator(info_json: dict[str, Any]) -> float:
    """Check for PyPI provenance/attestation indicators.
    
    PyPI is in the process of adding provenance features (PEP 740).
    For now, this is mostly a placeholder.
    
    Args:
        info_json: Full JSON from PyPI API
        
    Returns:
        Risk score: currently always 1.0 (no provenance checking yet)
    """
    # PyPI provenance is not widely deployed yet
    # In the future, check for:
    # - PEP 740 attestations
    # - Sigstore signatures
    # - Trusted publishers
    
    # Check if package uses trusted publishers (GitHub Actions)
    # This would require additional API calls to warehouse API
    
    return 1.0  # Default: no provenance verification


def has_trusted_publisher(info_json: dict[str, Any]) -> bool:
    """Check if PyPI package uses trusted publishers (placeholder).
    
    Args:
        info_json: Full JSON from PyPI API
        
    Returns:
        True if trusted publisher detected
    """
    # This would require checking PyPI's project API for trusted publishers
    # POST https://pypi.org/manage/project/{name}/settings/publishing/
    # For now, return False as a conservative default
    return False
