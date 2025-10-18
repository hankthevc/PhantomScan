"""Reputation and provenance enrichment."""

import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx


def parse_github_url(url: str) -> tuple[str, str] | None:
    """Parse GitHub URL to extract owner and repo.
    
    Args:
        url: Repository URL
        
    Returns:
        Tuple of (owner, repo) or None if not a GitHub URL
    """
    if not url:
        return None
    
    # Handle various GitHub URL formats
    patterns = [
        r"github\.com[:/]([^/]+)/([^/\.]+)",
        r"github\.com/([^/]+)/([^/]+)\.git",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
    
    return None


def get_repo_facts(
    repo_url: str | None,
    policy: dict[str, Any],
    offline: bool = False,
) -> tuple[int | None, int, bool, list[str]]:
    """Fetch repository facts from GitHub API.
    
    Args:
        repo_url: Repository URL
        policy: Policy configuration dict
        offline: If True, skip API calls
        
    Returns:
        Tuple of (repo_age_days, recent_commits, has_topics, reasons)
    """
    reasons = []
    
    if offline:
        reasons.append("Offline mode: skipped repo check")
        return None, 0, False, reasons
    
    if not repo_url:
        return None, 0, False, reasons
    
    # Parse GitHub URL
    parsed = parse_github_url(repo_url)
    if not parsed:
        reasons.append("Non-GitHub repository (no enrichment)")
        return None, 0, False, reasons
    
    owner, repo = parsed
    
    # Check if GitHub enrichment is enabled
    lookups = policy.get("lookups", {})
    if not lookups.get("enable_github", True):
        reasons.append("GitHub enrichment disabled")
        return None, 0, False, reasons
    
    # Get GitHub token if available
    gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {}
    if gh_token:
        headers["Authorization"] = f"token {gh_token}"
    
    headers["User-Agent"] = policy.get("network", {}).get("user_agent", "PhantomScan")
    
    try:
        # Fetch repository info
        api_url = f"https://api.github.com/repos/{owner}/{repo}"
        timeout = policy.get("sources", {}).get("pypi", {}).get("timeout", 10)
        
        with httpx.Client(timeout=timeout, headers=headers) as client:
            response = client.get(api_url)
            
            if response.status_code == 404:
                reasons.append("GitHub repository not found")
                return None, 0, False, reasons
            
            if response.status_code == 403:
                reasons.append("GitHub API rate limit (consider setting GH_TOKEN)")
                return None, 0, False, reasons
            
            response.raise_for_status()
            data = response.json()
        
        # Extract repo age
        created_at_str = data.get("created_at")
        repo_age_days = None
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                repo_age_days = (now - created_at).days
            except Exception:
                pass
        
        # Check recent activity (pushed_at)
        pushed_at_str = data.get("pushed_at")
        recent_commits = 0
        if pushed_at_str:
            try:
                pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                days_since_push = (datetime.now(timezone.utc) - pushed_at).days
                # Simple heuristic: if pushed within 90 days, consider it active
                if days_since_push < 90:
                    recent_commits = 1
            except Exception:
                pass
        
        # Check for topics
        topics = data.get("topics", [])
        has_topics = len(topics) > 0
        
        return repo_age_days, recent_commits, has_topics, reasons
        
    except Exception as e:
        reasons.append(f"GitHub API error: {type(e).__name__}")
        return None, 0, False, reasons


def get_osv_facts(
    ecosystem: str,
    name: str,
    policy: dict[str, Any],
    offline: bool = False,
) -> tuple[bool, list[str]]:
    """Check OSV database for known vulnerabilities.
    
    Args:
        ecosystem: Package ecosystem ("pypi" or "npm")
        name: Package name
        policy: Policy configuration dict
        offline: If True, skip API calls
        
    Returns:
        Tuple of (has_known_issues, reasons)
    """
    reasons = []
    
    if offline:
        reasons.append("Offline mode: skipped OSV check")
        return False, reasons
    
    # Check if OSV enrichment is enabled
    lookups = policy.get("lookups", {})
    if not lookups.get("enable_osv", True):
        reasons.append("OSV enrichment disabled")
        return False, reasons
    
    try:
        # Map ecosystem names to OSV format
        osv_ecosystem = "PyPI" if ecosystem.lower() == "pypi" else "npm"
        
        # Query OSV API
        api_url = "https://api.osv.dev/v1/query"
        payload = {
            "package": {"name": name, "ecosystem": osv_ecosystem}
        }
        
        timeout = policy.get("sources", {}).get("pypi", {}).get("timeout", 10)
        headers = {"User-Agent": policy.get("network", {}).get("user_agent", "PhantomScan")}
        
        with httpx.Client(timeout=timeout) as client:
            response = client.post(api_url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        # Check for vulnerabilities
        vulns = data.get("vulns", [])
        if vulns:
            reasons.append(f"Has {len(vulns)} known OSV vulnerabilities")
            return True, reasons
        
        return False, reasons
        
    except Exception as e:
        reasons.append(f"OSV API error: {type(e).__name__}")
        return False, reasons


def get_dependents_hint(ecosystem: str, name: str) -> int | None:
    """Get a rough estimate of package dependents (best-effort).
    
    This is a placeholder for future implementation. Could use:
    - libraries.io API
    - npm registry search
    - PyPI BigQuery data
    
    Args:
        ecosystem: Package ecosystem
        name: Package name
        
    Returns:
        Estimated dependent count or None
    """
    # Not implemented yet - would require additional APIs
    return None


def compute_repo_asymmetry(
    pkg_created_at: datetime,
    repo_age_days: int | None,
) -> float:
    """Compute asymmetry score between package creation and repo age.
    
    A brand-new package with a very old repo is normal.
    A package that's older than its repo is suspicious (repo created after package).
    
    Args:
        pkg_created_at: Package creation timestamp
        repo_age_days: Repository age in days (or None)
        
    Returns:
        Asymmetry score 0.0-1.0
    """
    if repo_age_days is None:
        # No repo data available
        return 0.0
    
    # Calculate package age
    now = datetime.now(timezone.utc)
    if pkg_created_at.tzinfo is None:
        pkg_created_at = pkg_created_at.replace(tzinfo=timezone.utc)
    
    pkg_age_days = (now - pkg_created_at).days
    
    # If repo is younger than package by significant margin, flag it
    age_diff = pkg_age_days - repo_age_days
    
    if age_diff <= 0:
        # Normal case: repo created before or same time as package
        return 0.0
    
    # Score increases with age difference (capped at 30 days)
    # Package published before repo existed is very suspicious
    return min(1.0, age_diff / 30.0)
