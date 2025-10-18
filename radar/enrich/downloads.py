"""Download statistics and anomaly detection."""

import httpx

from radar.utils import is_offline_mode, load_policy


def npm_weekly_downloads(name: str) -> int | None:
    """Get weekly download count from npm registry.

    Args:
        name: Package name

    Returns:
        Download count for last week, or None if unavailable
    """
    if is_offline_mode():
        return None

    try:
        policy = load_policy()
        
        # Check if downloads enrichment is enabled
        lookups = policy.heuristics.get("lookups", {})
        if not lookups.get("enable_npm_downloads", True):
            return None

        timeout = policy.sources.get("npm", {}).get("timeout", 10)
        user_agent = policy.network.get("user_agent", "PhantomScan/0.1.0")

        # npm downloads API
        api_url = lookups.get(
            "npm_downloads_api", "https://api.npmjs.org/downloads/point/last-week/{name}"
        )
        url = api_url.format(name=name)

        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers={"User-Agent": user_agent})

            if response.status_code == 404:
                # Package not found or no downloads
                return 0

            response.raise_for_status()
            data = response.json()

            return data.get("downloads", 0)

    except Exception:
        return None


def compute_download_anomaly(downloads: int | None, age_days: int) -> float:
    """Compute download anomaly score.

    Detects unusual download patterns (spikes for new packages, etc.)

    Args:
        downloads: Weekly download count
        age_days: Package age in days

    Returns:
        Anomaly score (0.0 = normal, 1.0 = highly anomalous)
    """
    if downloads is None:
        # No download data = can't compute anomaly
        return 0.0

    # Brand new packages (< 7 days) with high downloads are suspicious
    if age_days < 7:
        # Expect very low downloads for brand new packages
        # More than 1000/week for a brand new package is suspicious
        if downloads > 1000:
            # Map 1000-10000 downloads to 0.3-1.0 anomaly
            return min(0.3 + (downloads - 1000) / 15000.0, 1.0)

    # Very new packages (7-30 days) with sudden spikes
    elif age_days <= 30:
        # Expect low-moderate downloads
        # More than 10000/week is suspicious for such a new package
        if downloads > 10000:
            return min(0.5 + (downloads - 10000) / 40000.0, 1.0)

    # For older packages, we'd need historical baseline
    # For now, don't flag older packages based on downloads alone
    else:
        # Could implement spike detection by comparing to historical average
        # Placeholder: always return 0.0 for older packages
        pass

    return 0.0
