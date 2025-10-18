"""PyPI version flip analysis for detecting suspicious changes between releases."""

from typing import Any

import httpx
from rich.console import Console

from radar.types import PolicyConfig
from radar.utils import is_offline_mode

console = Console()


def _analyze_pypi_version_flip(
    info_json: dict[str, Any],
    policy: PolicyConfig,
) -> tuple[float, list[str]]:
    """Analyze version flip for PyPI package.
    
    Compares current version metadata with previous version to detect:
    - Sudden addition of console_scripts/entry_points
    - Dramatic increase in dependencies
    - Suspicious changes in project_urls
    
    Args:
        info_json: Full PyPI JSON API response
        policy: Policy configuration with thresholds
        
    Returns:
        Tuple of (risk_score, reasons_list)
    """
    if is_offline_mode():
        return 0.0, []

    reasons = []
    risk = 0.0

    try:
        info = info_json.get("info", {})
        releases = info_json.get("releases", {})
        current_version = info.get("version", "")

        if not current_version or not releases:
            return 0.0, []

        # Get sorted list of versions (latest first)
        version_list = sorted(
            [v for v in releases.keys() if releases[v]],
            reverse=True,
        )

        if len(version_list) < 2:
            # No previous version to compare
            return 0.0, []

        # Find previous version
        if current_version not in version_list:
            return 0.0, []

        current_idx = version_list.index(current_version)
        if current_idx >= len(version_list) - 1:
            # No previous version
            return 0.0, []

        previous_version = version_list[current_idx + 1]

        # Fetch previous version metadata
        package_name = info.get("name")
        if not package_name:
            return 0.0, []

        timeout = policy.heuristics.get("lookups", {}).get("timeout", 5)
        user_agent = policy.network.get("user_agent", "PhantomScan/0.1.0")

        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                prev_url = f"https://pypi.org/pypi/{package_name}/{previous_version}/json"
                response = client.get(prev_url, headers={"User-Agent": user_agent})

                if response.status_code != 200:
                    return 0.0, []

                prev_data = response.json()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not fetch previous version: {e}[/yellow]")
            return 0.0, []

        # Compare metadata
        current_info = info
        prev_info = prev_data.get("info", {})

        # 1. Check for console_scripts additions
        current_entry_points = current_info.get("entry_points")
        prev_entry_points = prev_info.get("entry_points")

        # Entry points are often in requires_dist or project metadata
        # For simplicity, check if they appear in the JSON structure
        current_has_scripts = "console_scripts" in str(current_entry_points) if current_entry_points else False
        prev_has_scripts = "console_scripts" in str(prev_entry_points) if prev_entry_points else False

        if current_has_scripts and not prev_has_scripts:
            risk = max(risk, 0.5)
            reasons.append(f"New console_scripts added in v{current_version}")

        # 2. Check for dramatic dependency increase
        current_deps = current_info.get("requires_dist") or []
        prev_deps = prev_info.get("requires_dist") or []

        if isinstance(current_deps, list) and isinstance(prev_deps, list):
            dep_increase = len(current_deps) - len(prev_deps)
            threshold = policy.heuristics.get("thresholds", {}).get("version_flip_dep_increase", 10)

            if dep_increase >= threshold:
                risk = max(risk, 0.5)
                reasons.append(
                    f"Dramatic dependency increase: +{dep_increase} dependencies "
                    f"({len(prev_deps)} → {len(current_deps)})"
                )

        # 3. Check for suspicious project_urls changes
        current_urls = current_info.get("project_urls") or {}
        prev_urls = prev_info.get("project_urls") or {}

        # Check if source/docs removed
        if prev_urls and not current_urls:
            risk = max(risk, 0.2)
            reasons.append("Project URLs removed entirely")
        elif prev_urls:
            important_keys = ["Source", "Repository", "Documentation", "Homepage"]
            for key in important_keys:
                if key in prev_urls and key not in current_urls:
                    risk = max(risk, 0.2)
                    reasons.append(f"Removed project URL: {key}")
                    break

        # Cap risk at 0.7
        risk = min(0.7, risk)

        return risk, reasons

    except Exception as e:
        console.print(f"[yellow]Warning: Version flip analysis error: {e}[/yellow]")
        return 0.0, []


def analyze_version_history(
    candidate_name: str,
    candidate_version: str,
    ecosystem: str,
    policy: PolicyConfig,
) -> tuple[float, list[str]]:
    """Analyze version history for suspicious changes.
    
    Currently supports PyPI only.
    
    Args:
        candidate_name: Package name
        candidate_version: Current version
        ecosystem: "pypi" or "npm"
        policy: Policy configuration
        
    Returns:
        Tuple of (risk_score, reasons_list)
    """
    if ecosystem.lower() != "pypi":
        return 0.0, []

    if is_offline_mode():
        return 0.0, []

    try:
        timeout = policy.heuristics.get("lookups", {}).get("timeout", 5)
        user_agent = policy.network.get("user_agent", "PhantomScan/0.1.0")

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            url = f"https://pypi.org/pypi/{candidate_name}/json"
            response = client.get(url, headers={"User-Agent": user_agent})

            if response.status_code != 200:
                return 0.0, []

            data = response.json()
            return _analyze_pypi_version_flip(data, policy)

    except Exception as e:
        console.print(f"[yellow]Warning: Version history analysis failed: {e}[/yellow]")
        return 0.0, []

