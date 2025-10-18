"""Version history analysis and flip detection."""

from datetime import datetime, timezone, timedelta
from typing import Any


def analyze_version_flip(
    ecosystem: str,
    name: str,
    metadata: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[float, list[str]]:
    """Analyze version history for suspicious version flips.
    
    A "version flip" is when a previously benign package suddenly adds
    dangerous features (install scripts, obfuscated code, etc.) in a new version.
    
    Args:
        ecosystem: Package ecosystem ("pypi" or "npm")
        name: Package name
        metadata: Full package metadata (packument for npm, JSON API for PyPI)
        policy: Policy configuration
        
    Returns:
        Tuple of (risk_score 0.0-1.0, list of reasons)
    """
    reasons = []
    
    if ecosystem.lower() == "npm":
        return _analyze_npm_version_flip(metadata, policy, reasons)
    elif ecosystem.lower() == "pypi":
        return _analyze_pypi_version_flip(metadata, policy, reasons)
    
    return 0.0, reasons


def _analyze_npm_version_flip(
    packument: dict[str, Any],
    policy: dict[str, Any],
    reasons: list[str],
) -> tuple[float, list[str]]:
    """Analyze npm version history for flips.
    
    Args:
        packument: Full npm packument
        policy: Policy configuration
        reasons: Reasons list to append to
        
    Returns:
        Tuple of (risk_score, updated reasons)
    """
    versions = packument.get("versions", {})
    time_data = packument.get("time", {})
    dist_tags = packument.get("dist-tags", {})
    latest_version = dist_tags.get("latest")
    
    if not latest_version or latest_version not in versions:
        return 0.0, reasons
    
    # Get version flip window from policy
    flip_window = policy.get("thresholds", {}).get("version_flip_window", 30)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=flip_window)
    
    # Analyze latest version
    latest_data = versions[latest_version]
    latest_scripts = latest_data.get("scripts", {})
    latest_has_install = any(
        key in latest_scripts for key in ["install", "preinstall", "postinstall"]
    )
    
    # Check if latest version was published within flip window
    latest_time_str = time_data.get(latest_version)
    if not latest_time_str:
        return 0.0, reasons
    
    try:
        latest_time = datetime.fromisoformat(latest_time_str.replace("Z", "+00:00"))
        if latest_time < cutoff_date:
            # Latest version is too old to be a "flip"
            return 0.0, reasons
    except Exception:
        return 0.0, reasons
    
    # Find previous versions within window
    recent_versions = []
    for ver, ver_time_str in time_data.items():
        if ver in versions and ver != latest_version:
            try:
                ver_time = datetime.fromisoformat(ver_time_str.replace("Z", "+00:00"))
                if ver_time >= cutoff_date:
                    recent_versions.append((ver, ver_time, versions[ver]))
            except Exception:
                continue
    
    # Sort by time
    recent_versions.sort(key=lambda x: x[1])
    
    # Check if previous versions lacked install scripts
    if latest_has_install and recent_versions:
        # Check if any recent previous version lacked install scripts
        for ver, ver_time, ver_data in recent_versions[-3:]:  # Check last 3 versions
            prev_scripts = ver_data.get("scripts", {})
            prev_has_install = any(
                key in prev_scripts for key in ["install", "preinstall", "postinstall"]
            )
            
            if not prev_has_install:
                reasons.append(
                    f"Version flip: {ver} had no install scripts, {latest_version} added them"
                )
                return 0.8, reasons
    
    return 0.0, reasons


def _analyze_pypi_version_flip(
    info_json: dict[str, Any],
    policy: dict[str, Any],
    reasons: list[str],
) -> tuple[float, list[str]]:
    """Analyze PyPI version history for flips.
    
    For PyPI, this is more limited since we can't easily compare
    code between versions without downloading all releases.
    
    Args:
        info_json: Full PyPI JSON API response
        policy: Policy configuration
        reasons: Reasons list to append to
        
    Returns:
        Tuple of (risk_score, updated reasons)
    """
    info = info_json.get("info", {})
    releases = info_json.get("releases", {})
    latest_version = info.get("version")
    
    if not latest_version or latest_version not in releases:
        return 0.0, reasons
    
    # Get version flip window from policy
    flip_window = policy.get("thresholds", {}).get("version_flip_window", 30)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=flip_window)
    
    # Check if latest version was uploaded recently
    latest_files = releases.get(latest_version, [])
    if not latest_files:
        return 0.0, reasons
    
    latest_upload = None
    for file_info in latest_files:
        upload_time_str = file_info.get("upload_time_iso_8601")
        if upload_time_str:
            try:
                upload_time = datetime.fromisoformat(upload_time_str.replace("Z", "+00:00"))
                if latest_upload is None or upload_time > latest_upload:
                    latest_upload = upload_time
            except Exception:
                continue
    
    if not latest_upload or latest_upload < cutoff_date:
        # Latest version is too old to be a "flip"
        return 0.0, reasons
    
    # For PyPI, we would need to download and compare artifacts
    # to detect content changes. This is expensive and left as future work.
    # For now, we check for rapid version bumps as a weak signal.
    
    recent_count = 0
    for version, files in releases.items():
        if version != latest_version and files:
            for file_info in files:
                upload_str = file_info.get("upload_time_iso_8601")
                if upload_str:
                    try:
                        upload_time = datetime.fromisoformat(upload_str.replace("Z", "+00:00"))
                        if upload_time >= cutoff_date:
                            recent_count += 1
                            break
                    except Exception:
                        continue
    
    # If many versions were pushed in the flip window, that's mildly suspicious
    if recent_count >= 5:
        reasons.append(f"Rapid versioning: {recent_count} versions in {flip_window} days")
        return 0.3, reasons
    
    return 0.0, reasons
