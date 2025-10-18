"""Reputation and provenance enrichment."""

import os
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from radar.utils import is_offline_mode, load_policy


def get_repo_facts(repo_url: str | None) -> tuple[int | None, int, bool, list[str]]:
    """Get repository facts from GitHub.

    Args:
        repo_url: Repository URL (GitHub only)

    Returns:
        Tuple of (repo_age_days, recent_commits, has_topics, reasons)
    """
    if not repo_url or is_offline_mode():
        return None, 0, False, ["Offline mode or no repo URL"]

    # Parse GitHub repo (owner/repo)
    github_match = re.search(r"github\.com[:/]([^/]+)/([^/\s.]+)", repo_url)
    if not github_match:
        return None, 0, False, ["Not a GitHub repository"]

    owner, repo = github_match.groups()
    repo = repo.removesuffix(".git")

    try:
        policy = load_policy()
        timeout = policy.sources.get("pypi", {}).get("timeout", 10)
        user_agent = policy.network.get("user_agent", "PhantomScan/0.1.0")

        # Check for GitHub token
        gh_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        headers = {"User-Agent": user_agent}
        if gh_token:
            headers["Authorization"] = f"token {gh_token}"

        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            # Get repo metadata
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = client.get(api_url, headers=headers)

            if response.status_code == 404:
                return None, 0, False, ["Repository not found"]
            elif response.status_code == 403:
                return None, 0, False, ["GitHub API rate limited"]

            response.raise_for_status()
            repo_data = response.json()

            # Extract repo age
            created_at_str = repo_data.get("created_at")
            repo_age_days = None
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                repo_age_days = (datetime.now(timezone.utc) - created_at).days

            # Check for topics
            has_topics = len(repo_data.get("topics", [])) > 0

            # Get recent commits (last 30 days)
            try:
                since_date = datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%dT%H:%M:%SZ")
                commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits"
                commits_response = client.get(
                    commits_url, headers=headers, params={"since": since_date, "per_page": 100}
                )
                recent_commits = 0
                if commits_response.status_code == 200:
                    recent_commits = len(commits_response.json())
            except Exception:
                recent_commits = 0

            reasons = []
            if repo_age_days is not None and repo_age_days < 30:
                reasons.append(f"Repository only {repo_age_days} days old")
            if recent_commits == 0:
                reasons.append("No recent commits (last 30 days)")
            if not has_topics:
                reasons.append("Repository has no topics")

            return repo_age_days, recent_commits, has_topics, reasons

    except Exception as e:
        return None, 0, False, [f"GitHub API error: {str(e)[:50]}"]


def get_osv_facts(ecosystem: str, name: str) -> tuple[bool, list[str]]:
    """Query OSV database for known vulnerabilities.

    Args:
        ecosystem: Package ecosystem (PyPI, npm)
        name: Package name

    Returns:
        Tuple of (has_known_issues, reasons)
    """
    if is_offline_mode():
        return False, ["Offline mode"]

    # Map ecosystem names
    ecosystem_map = {"pypi": "PyPI", "npm": "npm"}
    osv_ecosystem = ecosystem_map.get(ecosystem.lower(), ecosystem)

    try:
        policy = load_policy()
        
        # Check if OSV enrichment is enabled
        lookups = policy.heuristics.get("lookups", {})
        if not lookups.get("enable_osv", True):
            return False, ["OSV enrichment disabled"]

        timeout = policy.sources.get("pypi", {}).get("timeout", 10)
        user_agent = policy.network.get("user_agent", "PhantomScan/0.1.0")

        with httpx.Client(timeout=timeout) as client:
            osv_url = lookups.get("osv_api", "https://api.osv.dev/v1/query")
            response = client.post(
                osv_url,
                json={"package": {"name": name, "ecosystem": osv_ecosystem}},
                headers={"User-Agent": user_agent},
            )

            if response.status_code != 200:
                return False, ["OSV API unavailable"]

            data = response.json()
            vulns = data.get("vulns", [])

            if vulns:
                reasons = [f"Has {len(vulns)} known vulnerabilities in OSV database"]
                return True, reasons

            return False, []

    except Exception:
        return False, ["OSV query failed"]


def get_dependents_hint(ecosystem: str, name: str) -> int | None:
    """Get hint about number of dependents (cheap heuristics only).

    Args:
        ecosystem: Package ecosystem
        name: Package name

    Returns:
        Number of dependents, or None if unavailable
    """
    # Placeholder: This would require scraping or paid APIs
    # For now, return None (not implemented)
    # Future: Could use libraries.io API, npm registry, etc.
    return None


def compute_repo_asymmetry(pkg_created_at: datetime, repo_age_days: int | None) -> float:
    """Compute asymmetry between package and repository age.

    High asymmetry = package created long after repo (or vice versa) = suspicious

    Args:
        pkg_created_at: Package creation timestamp
        repo_age_days: Repository age in days

    Returns:
        Asymmetry score (0.0 = aligned, 1.0 = high asymmetry)
    """
    if repo_age_days is None:
        # No repo = can't compute asymmetry (handled by repo_missing score)
        return 0.0

    # Ensure timezone-aware
    if pkg_created_at.tzinfo is None:
        pkg_created_at = pkg_created_at.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    pkg_age_days = (now - pkg_created_at).days

    # Compute age difference
    age_diff = abs(pkg_age_days - repo_age_days)

    # Normalize to 0-1 scale
    # If diff > 180 days (6 months), consider it highly suspicious
    asymmetry = min(age_diff / 180.0, 1.0)

    return asymmetry
