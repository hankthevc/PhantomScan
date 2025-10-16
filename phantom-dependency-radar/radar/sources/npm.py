"""npm package data source."""

from datetime import datetime
from typing import List, Optional

from rich.console import Console

from ..types import Ecosystem, PackageCandidate
from .base import PackageSource

console = Console()


class NPMSource(PackageSource):
    """npm package data source using CouchDB changes feed."""
    
    def __init__(self, timeout: float = 30.0, retries: int = 3):
        super().__init__(Ecosystem.NPM, timeout, retries)
        
        self.changes_feed_url = "https://replicate.npmjs.com/_changes"
    
    def get_offline_seed_path(self) -> str:
        """Get path to offline seed data file."""
        return "data/samples/npm_seed.jsonl"
    
    def fetch_recent_packages(self, limit: int = 200) -> List[PackageCandidate]:
        """
        Fetch recent packages from npm changes feed.
        
        Args:
            limit: Maximum number of packages to fetch
            
        Returns:
            List of PackageCandidate objects
        """
        console.print(f"[blue]Fetching recent packages from npm (limit: {limit})[/blue]")
        
        try:
            # Fetch changes feed
            params = {
                'descending': 'true',
                'limit': min(limit * 2, 1000),  # Fetch more to account for filtering
                'include_docs': 'true'
            }
            
            response = self._retry_request(self.changes_feed_url, params=params)
            data = response.json()
            
            packages = []
            processed = 0
            
            for result in data.get('results', []):
                if processed >= limit:
                    break
                
                doc = result.get('doc', {})
                if not doc or doc.get('_deleted'):
                    continue
                
                package = self._parse_package_data(doc)
                if package:
                    packages.append(package)
                    processed += 1
                    
                    if processed % 20 == 0:
                        console.print(f"[blue]Processed {processed}/{limit} packages[/blue]")
            
            console.print(f"[green]Successfully fetched {len(packages)} npm packages[/green]")
            return packages
            
        except Exception as e:
            console.print(f"[red]Failed to fetch from npm changes feed: {e}[/red]")
            return []
    
    def _parse_package_data(self, raw_data: dict) -> Optional[PackageCandidate]:
        """
        Parse npm package document into PackageCandidate.
        
        Args:
            raw_data: Raw package data from npm CouchDB
            
        Returns:
            PackageCandidate object or None if parsing fails
        """
        try:
            # Basic package info
            name = raw_data.get('_id', '').strip()
            if not name or name.startswith('_'):
                return None
            
            # Skip scoped packages that are likely internal
            if name.startswith('@') and '/' in name:
                scope = name.split('/')[0]
                # Skip some known internal scopes
                internal_scopes = ['@types', '@babel', '@eslint', '@typescript-eslint']
                if scope in internal_scopes:
                    return None
            
            # Get latest version info
            versions = raw_data.get('versions', {})
            dist_tags = raw_data.get('dist-tags', {})
            latest_version = dist_tags.get('latest', '')
            
            if not latest_version or latest_version not in versions:
                # Fallback to last version
                if versions:
                    latest_version = list(versions.keys())[-1]
                else:
                    return None
            
            version_info = versions.get(latest_version, {})
            
            # Package metadata
            description = version_info.get('description', '') or raw_data.get('description', '')
            
            # Author info
            author = ''
            author_info = version_info.get('author') or raw_data.get('author')
            if isinstance(author_info, dict):
                author = author_info.get('name', '')
            elif isinstance(author_info, str):
                author = author_info
            
            # Maintainers
            maintainers = raw_data.get('maintainers', [])
            maintainers_count = len(maintainers) if maintainers else 1
            
            # Repository info
            repository_url = None
            homepage_url = version_info.get('homepage')
            
            repo_info = version_info.get('repository') or raw_data.get('repository')
            if isinstance(repo_info, dict):
                repo_url = repo_info.get('url', '')
                if repo_url:
                    # Clean up git URLs
                    if repo_url.startswith('git+'):
                        repo_url = repo_url[4:]
                    if repo_url.endswith('.git'):
                        repo_url = repo_url[:-4]
                    repository_url = repo_url
            elif isinstance(repo_info, str):
                repository_url = repo_info
            
            # Creation date
            created_at = None
            time_info = raw_data.get('time', {})
            created_time = time_info.get('created')
            
            if created_time:
                try:
                    created_at = datetime.fromisoformat(created_time.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            # Fallback to current time
            if created_at is None:
                created_at = datetime.utcnow()
            
            # Updated date
            updated_at = None
            modified_time = time_info.get('modified')
            if modified_time:
                try:
                    updated_at = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            # Check for install scripts
            has_install_scripts = False
            scripts = version_info.get('scripts', {})
            if scripts:
                dangerous_scripts = ['install', 'preinstall', 'postinstall']
                has_install_scripts = any(script in scripts for script in dangerous_scripts)
            
            package = PackageCandidate(
                name=name,
                ecosystem=Ecosystem.NPM,
                version=latest_version,
                created_at=created_at,
                updated_at=updated_at,
                description=description[:500] if description else None,  # Truncate long descriptions
                author=author[:100] if author else None,
                maintainers_count=max(1, maintainers_count),
                repository_url=repository_url,
                homepage_url=homepage_url,
                has_install_scripts=has_install_scripts,
                raw_data=raw_data
            )
            
            return package
            
        except Exception as e:
            console.print(f"[yellow]Failed to parse npm package data: {e}[/yellow]")
            return None