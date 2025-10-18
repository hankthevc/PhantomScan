"""PyPI package source implementation."""

from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
from rich.console import Console

from radar.types import Ecosystem, PackageCandidate
from radar.sources.base import PackageSource
from radar.utils import is_offline_mode, load_jsonl, load_policy

console = Console()


class PyPISource(PackageSource):
    """Fetch package metadata from PyPI."""

    def __init__(self) -> None:
        """Initialize PyPI source."""
        self.policy = load_policy()
        self.config = self.policy.sources["pypi"]

        if not is_offline_mode():
            self.client = httpx.Client(
                timeout=self.config["timeout"],
                headers={"User-Agent": self.policy.network["user_agent"]},
                follow_redirects=True,
            )
        else:
            self.client = None

    @property
    def ecosystem(self) -> Ecosystem:
        """Return PyPI ecosystem."""
        return Ecosystem.PYPI

    def fetch_recent(self, limit: int = 400) -> list[PackageCandidate]:
        """Fetch recent packages from PyPI RSS and JSON API."""
        if is_offline_mode():
            return self._load_offline_data(limit)

        package_names = self._fetch_rss_packages(limit)
        candidates = []

        for name in package_names:
            try:
                candidate = self._fetch_package_metadata(name)
                if candidate:
                    candidates.append(candidate)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to fetch {name}: {e}[/yellow]")
                continue

        console.print(f"[green]✓ Fetched {len(candidates)} PyPI packages[/green]")
        return candidates

    def _fetch_rss_packages(self, limit: int) -> list[str]:
        """Fetch package names from PyPI RSS feeds."""
        names = set()

        # Fetch from both RSS feeds
        for feed_url in [self.config["rss_packages"], self.config["rss_updates"]]:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[: limit // 2]:
                    # Extract package name from title (format: "package-name version")
                    title = entry.get("title", "")
                    if " " in title:
                        name = title.split(" ")[0]
                        names.add(name)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to parse RSS {feed_url}: {e}[/yellow]")

        return list(names)[:limit]

    def _fetch_package_metadata(self, name: str) -> PackageCandidate | None:
        """Fetch detailed metadata for a package."""
        if not self.client:
            return None

        url = self.config["json_api"].format(name=name)

        for attempt in range(self.config["retries"]):
            try:
                response = self.client.get(url)
                if response.status_code == 404:
                    return None
                response.raise_for_status()

                data = response.json()
                return self._parse_package_json(data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                if attempt == self.config["retries"] - 1:
                    raise
            except Exception as e:
                if attempt == self.config["retries"] - 1:
                    raise

        return None

    def _parse_package_json(self, data: dict[str, Any]) -> PackageCandidate:
        """Parse PyPI JSON API response into PackageCandidate."""
        info = data.get("info", {})
        releases = data.get("releases", {})

        # Find earliest upload time across all releases
        earliest_time = None
        for release_files in releases.values():
            for file_info in release_files:
                upload_time_str = file_info.get("upload_time_iso_8601")
                if upload_time_str:
                    upload_time = datetime.fromisoformat(upload_time_str.replace("Z", "+00:00"))
                    if earliest_time is None or upload_time < earliest_time:
                        earliest_time = upload_time

        # Fallback to current time if no upload time found
        if earliest_time is None:
            earliest_time = datetime.now(timezone.utc)

        # Extract repository URL
        repo_url = None
        project_urls = info.get("project_urls") or {}
        for key in ["Source", "Repository", "Code", "GitHub", "GitLab"]:
            if key in project_urls:
                repo_url = project_urls[key]
                break

        # Preserve full metadata for enrichment
        # (already done via raw_metadata=data)
        return PackageCandidate(
            ecosystem=Ecosystem.PYPI,
            name=info.get("name", ""),
            version=info.get("version", ""),
            created_at=earliest_time,
            homepage=info.get("home_page") or info.get("project_url"),
            repository=repo_url,
            maintainers_count=1,  # PyPI doesn't expose maintainer count easily
            has_install_scripts=False,  # Not applicable to PyPI
            description=info.get("summary"),
            raw_metadata=data,  # Full JSON including info, releases, urls
        )

    def _load_offline_data(self, limit: int) -> list[PackageCandidate]:
        """Load package data from offline seed file."""
        from pathlib import Path

        seed_path = Path("data/samples/pypi_seed.jsonl")
        if not seed_path.exists():
            console.print("[yellow]Warning: PyPI seed file not found[/yellow]")
            return []

        data = load_jsonl(seed_path)
        candidates = []

        for item in data[:limit]:
            try:
                candidate = self._parse_package_json(item)
                candidates.append(candidate)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to parse seed data: {e}[/yellow]")

        console.print(f"[cyan]✓ Loaded {len(candidates)} PyPI packages (offline)[/cyan]")
        return candidates

    def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            self.client.close()
