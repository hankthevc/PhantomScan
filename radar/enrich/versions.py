"""Version history analysis for detecting suspicious changes."""

from datetime import datetime, timedelta, timezone
from typing import Any

from radar.utils import load_policy


def analyze_version_flip(
    ecosystem: str, name: str, packument: dict[str, Any] | None
) -> tuple[float, list[str]]:
    """Analyze version history for suspicious flips.

    A "flip" is when a new version suddenly adds risky behavior
    (e.g., install scripts, suspicious code) that wasn't in previous versions.

    Args:
        ecosystem: Package ecosystem
        name: Package name
        packument: Full package document (npm) or releases dict (PyPI)

    Returns:
        Tuple of (risk_score, reasons)
    """
    if not packument:
        return 0.0, []

    reasons = []
    risk = 0.0

    try:
        policy = load_policy()
        thresholds = policy.heuristics.get("thresholds", {})
        flip_window_days = thresholds.get("version_flip_window", 30)

        if ecosystem.lower() == "npm":
            risk, reasons = _analyze_npm_version_flip(packument, flip_window_days)
        elif ecosystem.lower() == "pypi":
            risk, reasons = _analyze_pypi_version_flip(packument, flip_window_days)

    except Exception:
        pass

    return risk, reasons


def _analyze_npm_version_flip(packument: dict[str, Any], window_days: int) -> tuple[float, list[str]]:
    """Analyze npm package version history."""
    reasons = []
    risk = 0.0

    versions_data = packument.get("versions", {})
    time_data = packument.get("time", {})
    dist_tags = packument.get("dist-tags", {})
    latest_version = dist_tags.get("latest")

    if not latest_version or latest_version not in versions_data:
        return 0.0, []

    latest_pkg = versions_data[latest_version]
    latest_time_str = time_data.get(latest_version)

    if not latest_time_str:
        return 0.0, []

    latest_time = datetime.fromisoformat(latest_time_str.replace("Z", "+00:00"))
    window_start = latest_time - timedelta(days=window_days)

    # Check if latest has install scripts
    latest_scripts = latest_pkg.get("scripts", {})
    latest_has_install = any(
        key in latest_scripts for key in ["install", "preinstall", "postinstall"]
    )

    if not latest_has_install:
        # No install scripts in latest = no flip concern
        return 0.0, []

    # Find previous version within window
    previous_versions = []
    for ver, ver_time_str in time_data.items():
        if ver in ["created", "modified"] or ver == latest_version:
            continue

        try:
            ver_time = datetime.fromisoformat(ver_time_str.replace("Z", "+00:00"))
            if window_start <= ver_time < latest_time:
                previous_versions.append((ver, ver_time))
        except Exception:
            continue

    # Sort by time descending
    previous_versions.sort(key=lambda x: x[1], reverse=True)

    # Check if previous version (within window) lacked install scripts
    for prev_ver, _ in previous_versions:
        if prev_ver not in versions_data:
            continue

        prev_pkg = versions_data[prev_ver]
        prev_scripts = prev_pkg.get("scripts", {})
        prev_has_install = any(
            key in prev_scripts for key in ["install", "preinstall", "postinstall"]
        )

        if not prev_has_install:
            # Found a version flip: previous lacked scripts, latest has them
            risk = 0.7
            reasons.append(
                f"Version flip: v{prev_ver} had no install scripts, "
                f"v{latest_version} added them within {window_days} days"
            )
            break

    return risk, reasons


def _analyze_pypi_version_flip(info_json: dict[str, Any], window_days: int) -> tuple[float, list[str]]:
    """Analyze PyPI package version history.

    Note: PyPI doesn't have install scripts like npm, so we check for
    other indicators (e.g., sudden addition of dependencies, entry points).
    This is a simplified heuristic.
    """
    reasons = []
    risk = 0.0

    # For PyPI, version flip detection is less straightforward
    # We could check for:
    # - Sudden addition of many dependencies
    # - Addition of entry points (console_scripts)
    # - Changes in project URLs

    # Placeholder: simplified implementation
    # In a full implementation, we'd fetch multiple versions and compare

    info = info_json.get("info", {})
    releases = info_json.get("releases", {})

    current_version = info.get("version")
    if not current_version or current_version not in releases:
        return 0.0, []

    # Check if current version has entry points
    # (Would require downloading and inspecting setup.py or metadata)
    # For now, this is a placeholder

    # Simplified: If package has very recent version with significantly
    # different metadata, flag it (but this requires historical comparison)
    # Skip for now - full implementation would fetch previous versions

    return 0.0, []
