"""
Registry existence checking for npm and PyPI packages.

This module provides fast existence checks against public registries
to filter out non-existent package names from the main feed.
"""

import httpx

from radar.types import PolicyConfig
from radar.utils import is_offline_mode


def exists_in_registry(ecosystem: str, name: str, policy: PolicyConfig) -> tuple[bool, str]:
    """
    Check if a package exists in its registry.

    Args:
        ecosystem: Package ecosystem ("npm" or "pypi")
        name: Package name to check
        policy: Policy configuration with network settings

    Returns:
        Tuple of (exists, reason) where:
        - exists: True if package found in registry, False otherwise
        - reason: One of "ok", "404", "timeout", "offline", "error"

    Examples:
        >>> policy = load_policy()
        >>> exists, reason = exists_in_registry("npm", "express", policy)
        >>> assert exists and reason == "ok"
    """
    # Honor offline mode
    if is_offline_mode():
        return False, "offline"

    timeout = policy.network.get("registry_timeout_seconds", 4)
    user_agent = policy.network.get("user_agent", "PhantomScan/0.1.0 (security research)")

    try:
        if ecosystem == "npm":
            return _check_npm_existence(name, timeout, user_agent)
        if ecosystem == "pypi":
            return _check_pypi_existence(name, timeout, user_agent)
        # Unknown ecosystem - treat as not found
        return False, "error"
    except Exception:
        return False, "error"


def _check_npm_existence(name: str, timeout: float, user_agent: str) -> tuple[bool, str]:
    """Check npm registry for package existence."""
    url = f"https://registry.npmjs.org/{name}"

    try:
        with httpx.Client(timeout=timeout) as client:
            # Use HEAD for efficiency, fallback to GET if needed
            response = client.head(url, headers={"User-Agent": user_agent})

            if response.status_code == 200:
                return True, "ok"
            if response.status_code == 404:
                return False, "404"
            # Try GET as fallback for some registries that don't support HEAD
            response = client.get(url, headers={"User-Agent": user_agent})
            if response.status_code == 200:
                return True, "ok"
            if response.status_code == 404:
                return False, "404"
            return False, "error"
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception:
        return False, "error"


def _check_pypi_existence(name: str, timeout: float, user_agent: str) -> tuple[bool, str]:
    """Check PyPI registry for package existence."""
    url = f"https://pypi.org/pypi/{name}/json"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, headers={"User-Agent": user_agent})

            if response.status_code == 200:
                return True, "ok"
            if response.status_code == 404:
                return False, "404"
            return False, "error"
    except httpx.TimeoutException:
        return False, "timeout"
    except Exception:
        return False, "error"
