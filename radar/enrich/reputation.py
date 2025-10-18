"""Reputation and dependents enrichment via external APIs."""

import os

import httpx
from rich.console import Console

from radar.types import PolicyConfig
from radar.utils import is_offline_mode

console = Console()


def get_dependents_hint(
    ecosystem: str,
    name: str,
    policy: PolicyConfig,
) -> int | None:
    """Get dependents count hint from libraries.io.
    
    Requires LIBRARIES_IO_KEY environment variable.
    
    Args:
        ecosystem: "pypi" or "npm"
        name: Package name
        policy: Policy configuration
        
    Returns:
        Dependents count or None if unavailable
    """
    if is_offline_mode():
        return None

    # Check if feature is enabled
    lookups = policy.heuristics.get("lookups", {})
    if not lookups.get("enable_dependents", False):
        return None

    # Check for API key
    api_key = os.environ.get("LIBRARIES_IO_KEY")
    if not api_key:
        return None

    try:
        # Map ecosystem names
        ecosystem_map = {
            "pypi": "Pypi",
            "npm": "NPM",
        }

        lib_ecosystem = ecosystem_map.get(ecosystem.lower())
        if not lib_ecosystem:
            return None

        api_base = lookups.get("libraries_io_api", "https://libraries.io/api")
        timeout = lookups.get("timeout", 5)

        url = f"{api_base}/{lib_ecosystem}/{name}/dependents"
        params: dict[str, str | int] = {
            "api_key": api_key,
            "per_page": 1,
        }

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, params=params)

            if response.status_code == 404:
                # Package not found in libraries.io
                return 0

            if response.status_code != 200:
                return None

            # Try to get total from X-Total header
            total_header = response.headers.get("X-Total")
            if total_header:
                try:
                    return int(total_header)
                except ValueError:
                    pass

            # Fallback: count items in response
            data = response.json()
            if isinstance(data, list):
                # If we got results, there's at least 1
                return len(data) if data else 0

            return None

    except Exception as e:
        console.print(f"[yellow]Warning: Dependents lookup failed: {e}[/yellow]")
        return None


def adjust_score_by_dependents(
    dependents_count: int | None,
    policy: PolicyConfig,
) -> tuple[float, list[str]]:
    """Adjust reputation score based on dependents count.
    
    Args:
        dependents_count: Number of dependents (or None)
        policy: Policy configuration
        
    Returns:
        Tuple of (adjustment_factor, reasons_list)
        Adjustment factor: multiply existing scores by this (0.7-1.0)
    """
    if dependents_count is None:
        return 1.0, []

    reasons = []
    lookups = policy.heuristics.get("lookups", {})
    low_threshold = lookups.get("dependents_low_threshold", 0)
    high_threshold = lookups.get("dependents_high_threshold", 50)

    if dependents_count <= low_threshold:
        reasons.append("No known dependents (libraries.io)")
        return 1.0, reasons  # Keep score as-is, already suspicious
    if dependents_count >= high_threshold:
        reasons.append(f"Established package with {dependents_count}+ dependents")
        return 0.7, reasons  # Reduce suspicion by 30%
    # Moderate dependents count
    reasons.append(f"Package has {dependents_count} dependents")
    return 0.85, reasons  # Small reduction

