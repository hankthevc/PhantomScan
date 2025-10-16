"""PyPI package data source."""

import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urljoin

import feedparser
from rich.console import Console

from ..types import Ecosystem, PackageCandidate
from .base import PackageSource

console = Console()


class PyPISource(PackageSource):
    """PyPI package data source using RSS feeds and JSON API."""
    
    def __init__(self, timeout: float = 30.0, retries: int = 3):
        super().__init__(Ecosystem.PYPI, timeout, retries)
        
        self.rss_feeds = [
            "https://pypi.org/rss/packages.xml",
            "https://pypi.org/rss/updates.xml"
        ]
        
        self.json_api_base = "https://pypi.org/pypi"
    
    def get_offline_seed_path(self) -> str:
        """Get path to offline seed data file."""
        return "data/samples/pypi_seed.jsonl"
    
    def fetch_recent_packages(self, limit: int = 200) -> List[PackageCandidate]:
        """
        Fetch recent packages from PyPI RSS feeds and JSON API.
        
        Args:
            limit: Maximum number of packages to fetch
            
        Returns:
            List of PackageCandidate objects
        """
        console.print(f"[blue]Fetching recent packages from PyPI (limit: {limit})[/blue]")
        
        # Get package names from RSS feeds
        package_names = set()
        
        for rss_url in self.rss_feeds:
            try:
                console.print(f"[blue]Fetching RSS feed: {rss_url}[/blue]")
                response = self._retry_request(rss_url)
                
                # Parse RSS feed
                feed = feedparser.parse(response.text)
                
                for entry in feed.entries:
                    # Extract package name from title or link
                    package_name = self._extract_package_name(entry)
                    if package_name:
                        package_names.add(package_name.lower())
                        
                        if len(package_names) >= limit:
                            break
                
                console.print(f"[green]Found {len(package_names)} packages from RSS feed[/green]")
                
            except Exception as e:
                console.print(f"[yellow]Failed to fetch RSS feed {rss_url}: {e}[/yellow]")
                continue
        
        # Fetch detailed package info
        packages = []
        processed = 0
        
        for package_name in list(package_names)[:limit]:
            if processed >= limit:
                break
                
            try:
                package = self._fetch_package_details(package_name)
                if package:
                    packages.append(package)
                processed += 1
                
                # Rate limiting
                if processed % 10 == 0:
                    console.print(f"[blue]Processed {processed}/{min(len(package_names), limit)} packages[/blue]")
                    
            except Exception as e:
                console.print(f"[yellow]Failed to fetch details for {package_name}: {e}[/yellow]")
                continue
        
        console.print(f"[green]Successfully fetched {len(packages)} PyPI packages[/green]")
        return packages
    
    def _extract_package_name(self, entry) -> Optional[str]:
        """Extract package name from RSS entry."""
        # Try to extract from title (e.g., "package-name 1.0.0")
        title = getattr(entry, 'title', '')
        if title:
            # Remove version and clean up
            name_match = re.match(r'^([a-zA-Z0-9\-\._]+)', title)
            if name_match:
                return name_match.group(1)
        
        # Try to extract from link
        link = getattr(entry, 'link', '')
        if link:
            # Extract from URL like https://pypi.org/project/package-name/
            link_match = re.search(r'/project/([^/]+)/?', link)
            if link_match:
                return link_match.group(1)
        
        return None
    
    def _fetch_package_details(self, package_name: str) -> Optional[PackageCandidate]:
        """Fetch detailed package information from PyPI JSON API."""
        url = f"{self.json_api_base}/{package_name}/json"
        
        try:
            response = self._retry_request(url)
            data = response.json()
            
            return self._parse_package_data(data)
            
        except Exception as e:
            console.print(f"[yellow]Failed to fetch details for {package_name}: {e}[/yellow]")
            return None
    
    def _parse_package_data(self, raw_data: dict) -> Optional[PackageCandidate]:
        """
        Parse PyPI JSON API response into PackageCandidate.
        
        Args:
            raw_data: Raw package data from PyPI JSON API
            
        Returns:
            PackageCandidate object or None if parsing fails
        """
        try:
            info = raw_data.get('info', {})
            
            # Basic package info
            name = info.get('name', '').strip().lower()
            if not name:
                return None
            
            version = info.get('version', '')
            description = info.get('summary', '') or info.get('description', '')
            author = info.get('author', '') or info.get('maintainer', '')
            
            # URLs
            repository_url = None
            homepage_url = info.get('home_page')
            
            # Try to find repository URL from project URLs
            project_urls = info.get('project_urls') or {}
            for key, url in project_urls.items():
                if url and ('github' in url.lower() or 'gitlab' in url.lower() or 'repository' in key.lower()):
                    repository_url = url
                    break
            
            # If no repository found, check if homepage is a repo
            if not repository_url and homepage_url:
                if 'github' in homepage_url.lower() or 'gitlab' in homepage_url.lower():
                    repository_url = homepage_url
            
            # Get creation date from releases
            created_at = None
            releases = raw_data.get('releases', {})
            
            if releases:
                # Find the earliest release date
                earliest_date = None
                for version_releases in releases.values():
                    if version_releases:
                        for release in version_releases:
                            upload_time = release.get('upload_time_iso_8601')
                            if upload_time:
                                try:
                                    release_date = datetime.fromisoformat(upload_time.replace('Z', '+00:00'))
                                    if earliest_date is None or release_date < earliest_date:
                                        earliest_date = release_date
                                except ValueError:
                                    continue
                
                created_at = earliest_date
            
            # Fallback to current time if no creation date found
            if created_at is None:
                created_at = datetime.utcnow()
            
            # Maintainers count (approximate from maintainer_email)
            maintainers_count = 1  # Default to 1
            if info.get('maintainer_email'):
                # Count comma-separated emails
                emails = info.get('maintainer_email', '').split(',')
                maintainers_count = len([e for e in emails if '@' in e])
            
            package = PackageCandidate(
                name=name,
                ecosystem=Ecosystem.PYPI,
                version=version,
                created_at=created_at,
                updated_at=None,  # PyPI doesn't provide last update time easily
                description=description[:500] if description else None,  # Truncate long descriptions
                author=author[:100] if author else None,
                maintainers_count=max(1, maintainers_count),
                repository_url=repository_url,
                homepage_url=homepage_url,
                has_install_scripts=False,  # PyPI doesn't have install scripts like npm
                raw_data=raw_data
            )
            
            return package
            
        except Exception as e:
            console.print(f"[yellow]Failed to parse PyPI package data: {e}[/yellow]")
            return None