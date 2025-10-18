"""npm package source implementation."""

from datetime import UTC, datetime
from typing import Any

import httpx
from rich.console import Console

from radar.sources.base import PackageSource
from radar.types import Ecosystem, PackageCandidate
from radar.utils import is_offline_mode, load_jsonl, load_policy

console = Console()


class NpmSource(PackageSource):
    """Fetch package metadata from npm."""

    def __init__(self) -> None:
        """Initialize npm source."""
        self.policy = load_policy()
        self.config = self.policy.sources["npm"]

        if not is_offline_mode():
            self.client: httpx.Client | None = httpx.Client(
                timeout=self.config["timeout"],
                headers={"User-Agent": self.policy.network["user_agent"]},
                follow_redirects=True,
            )
        else:
            self.client = None

    @property
    def ecosystem(self) -> Ecosystem:
        """Return npm ecosystem."""
        return Ecosystem.NPM

    def fetch_recent(self, limit: int = 400) -> list[PackageCandidate]:
        """Fetch recent packages from npm changes feed."""
        if is_offline_mode():
            return self._load_offline_data(limit)

        if not self.client:
            return []

        try:
            # First get list of changed packages (without docs due to API limitations)
            url = f"{self.config['changes_feed']}?descending=true&limit={limit}"
            response = self.client.get(url)
            response.raise_for_status()

            data = response.json()
            candidates = []
            
            # Get package names from changes
            package_names = []
            for change in data.get("results", [])[:limit]:
                pkg_name = change.get("id", "")
                if pkg_name and not pkg_name.startswith("_"):
                    package_names.append(pkg_name)
            
            # Now fetch individual package docs (limit to prevent too many requests)
            console.print(f"[cyan]Fetching details for {min(len(package_names), 50)} recent npm packages...[/cyan]")
            for name in package_names[:50]:  # Limit to 50 to avoid rate limits
                try:
                    pkg_url = f"https://registry.npmjs.org/{name}"
                    pkg_response = self.client.get(pkg_url)
                    if pkg_response.status_code == 200:
                        doc = pkg_response.json()
                        candidate = self._parse_npm_doc(doc)
                        if candidate:
                            candidates.append(candidate)
                except Exception as e:
                    console.print(f"[yellow]Warning: Failed to fetch {name}: {e}[/yellow]")
                    continue

            console.print(f"[green]✓ Fetched {len(candidates)} npm packages[/green]")
            return candidates

        except Exception as e:
            console.print(f"[red]Error fetching npm changes: {e}[/red]")
            return []

    def _parse_npm_doc(self, doc: dict[str, Any]) -> PackageCandidate | None:
        """Parse npm document into PackageCandidate."""
        name = doc.get("name")
        if not name:
            return None

        # Extract creation time
        time_data = doc.get("time", {})
        created_str = time_data.get("created")
        if created_str:
            try:
                created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except Exception:
                created_at = datetime.now(UTC)
        else:
            created_at = datetime.now(UTC)

        # Get latest version
        dist_tags = doc.get("dist-tags", {})
        latest_version = dist_tags.get("latest", "0.0.0")

        # Extract repository
        repo_info = doc.get("repository", {})
        repo_url = None
        if isinstance(repo_info, dict):
            repo_url = repo_info.get("url")
        elif isinstance(repo_info, str):
            repo_url = repo_info

        # Extract homepage
        homepage = doc.get("homepage")

        # Count maintainers and check for disposable emails
        maintainers = doc.get("maintainers", [])
        maintainers_count = len(maintainers) if isinstance(maintainers, list) else 1

        # Check for disposable email domains
        disposable_email = False
        disposable_domains = self.policy.heuristics.get("disposable_email_domains", [])

        if isinstance(maintainers, list):
            for maintainer in maintainers:
                if isinstance(maintainer, dict):
                    email = maintainer.get("email", "")
                    if email:
                        # Check if email domain is in disposable list
                        email_lower = email.lower()
                        for domain in disposable_domains:
                            if domain in email_lower:
                                disposable_email = True
                                break
                if disposable_email:
                    break

        # Calculate maintainer age hint
        maintainers_age_hint_days = None
        if time_data.get("created"):
            try:
                created_time = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                age = (datetime.now(UTC) - created_time).days
                maintainers_age_hint_days = age
            except Exception:
                pass

        # Check for install scripts in latest version
        has_install_scripts = False
        versions = doc.get("versions", {})
        if latest_version in versions:
            latest_pkg = versions[latest_version]
            scripts = latest_pkg.get("scripts", {})
            if isinstance(scripts, dict):
                dangerous_scripts = {"install", "preinstall", "postinstall"}
                has_install_scripts = any(key in scripts for key in dangerous_scripts)

        return PackageCandidate(
            ecosystem=Ecosystem.NPM,
            name=name,
            version=latest_version,
            created_at=created_at,
            homepage=homepage,
            repository=repo_url,
            maintainers_count=maintainers_count,
            has_install_scripts=has_install_scripts,
            description=doc.get("description"),
            raw_metadata=doc,
            disposable_email=disposable_email,
            maintainers_age_hint_days=maintainers_age_hint_days,
        )

    def _load_offline_data(self, limit: int) -> list[PackageCandidate]:
        """Load package data from offline seed file."""
        from pathlib import Path

        seed_path = Path("data/samples/npm_seed.jsonl")
        if not seed_path.exists():
            console.print("[yellow]Warning: npm seed file not found[/yellow]")
            return []

        data = load_jsonl(seed_path)
        candidates = []

        for doc in data[:limit]:
            try:
                candidate = self._parse_npm_doc(doc)
                if candidate:
                    candidates.append(candidate)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to parse seed data: {e}[/yellow]")

        console.print(f"[cyan]✓ Loaded {len(candidates)} npm packages (offline)[/cyan]")
        return candidates

    def close(self) -> None:
        """Close HTTP client."""
        if self.client:
            self.client.close()
