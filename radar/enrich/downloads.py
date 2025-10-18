"""Download statistics and anomaly detection."""

from typing import Any

import httpx


def npm_weekly_downloads(name: str, policy: dict[str, Any], offline: bool = False) -> int | None:
    """Fetch weekly download count for npm package.
    
    Args:
        name: Package name
        policy: Policy configuration dict
        offline: If True, skip API call
        
    Returns:
        Weekly download count or None on error
    """
    if offline:
        return None
    
    # Check if npm downloads enrichment is enabled
    lookups = policy.get("lookups", {})
    if not lookups.get("enable_npm_downloads", True):
        return None
    
    try:
        api_url = f"https://api.npmjs.org/downloads/point/last-week/{name}"
        timeout = policy.get("sources", {}).get("npm", {}).get("timeout", 10)
        headers = {"User-Agent": policy.get("network", {}).get("user_agent", "PhantomScan")}
        
        with httpx.Client(timeout=timeout) as client:
            response = client.get(api_url, headers=headers)
            
            if response.status_code == 404:
                return 0  # Package not found or no downloads
            
            response.raise_for_status()
            data = response.json()
        
        downloads = data.get("downloads", 0)
        return downloads
        
    except Exception:
        return None


def compute_download_anomaly(downloads: int | None, age_days: int) -> float:
    """Compute download anomaly score based on downloads vs. package age.
    
    A brand-new package with very high downloads is suspicious (possible spam/bot).
    Established packages with high downloads are normal.
    
    Args:
        downloads: Weekly download count (or None)
        age_days: Package age in days
        
    Returns:
        Anomaly score 0.0-1.0
    """
    if downloads is None or downloads == 0:
        return 0.0
    
    # Very new packages (< 7 days) with high downloads are suspicious
    if age_days < 7:
        # Threshold: 1000+ downloads for a brand new package
        if downloads > 1000:
            return min(1.0, downloads / 10000)
        return 0.0
    
    # Newer packages (7-30 days) with very high downloads
    if age_days < 30:
        # Threshold: 10,000+ downloads for a 1-month-old package
        if downloads > 10000:
            return min(1.0, (downloads - 10000) / 50000)
        return 0.0
    
    # For older packages, high downloads are normal
    return 0.0


def estimate_download_baseline(age_days: int) -> int:
    """Estimate expected baseline downloads for package age.
    
    This is a rough heuristic for what's "normal" download activity.
    
    Args:
        age_days: Package age in days
        
    Returns:
        Estimated weekly download count
    """
    if age_days < 7:
        return 100
    elif age_days < 30:
        return 500
    elif age_days < 90:
        return 2000
    elif age_days < 365:
        return 5000
    else:
        return 10000


def detect_download_spike(
    current_downloads: int | None,
    baseline: int | None,
    spike_ratio: float = 5.0,
) -> tuple[bool, str]:
    """Detect if current downloads represent a spike vs. baseline.
    
    Args:
        current_downloads: Current weekly downloads
        baseline: Baseline/historical weekly downloads
        spike_ratio: Ratio threshold for spike detection
        
    Returns:
        Tuple of (is_spike, reason)
    """
    if current_downloads is None or baseline is None:
        return False, ""
    
    if baseline == 0:
        baseline = 1  # Avoid division by zero
    
    ratio = current_downloads / baseline
    
    if ratio >= spike_ratio:
        return True, f"Download spike: {ratio:.1f}x baseline"
    
    return False, ""
