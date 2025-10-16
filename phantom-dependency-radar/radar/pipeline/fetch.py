"""Package fetching pipeline component."""

from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console

from ..sources import NPMSource, PyPISource
from ..storage import get_storage
from ..types import Ecosystem, PackageCandidate, PolicyConfig
from ..utils import ProgressReporter, ensure_data_dirs, get_date_str, load_policy, save_jsonl

console = Console()


class PackageFetcher:
    """Fetches packages from multiple sources and stores raw data."""
    
    def __init__(self, policy: PolicyConfig = None):
        self.policy = policy or load_policy()
        self.storage = get_storage()
        
        # Initialize sources
        self.sources = {}
        
        if self.policy.sources.pypi.enabled:
            self.sources[Ecosystem.PYPI] = PyPISource(
                timeout=self.policy.sources.pypi.timeout_seconds,
                retries=3
            )
        
        if self.policy.sources.npm.enabled:
            self.sources[Ecosystem.NPM] = NPMSource(
                timeout=self.policy.sources.npm.timeout_seconds,
                retries=3
            )
    
    def fetch_packages(
        self, 
        ecosystems: Optional[List[str]] = None, 
        limit: Optional[int] = None, 
        date: Optional[str] = None
    ) -> List[PackageCandidate]:
        """
        Fetch packages from specified ecosystems.
        
        Args:
            ecosystems: List of ecosystems to fetch from (e.g., ['pypi', 'npm'])
            limit: Maximum packages to fetch per ecosystem
            date: Date string for storage (YYYY-MM-DD), defaults to today
            
        Returns:
            List of all fetched PackageCandidate objects
        """
        if date is None:
            date = get_date_str()
        
        if ecosystems is None:
            ecosystems = ['pypi', 'npm']
        
        ensure_data_dirs()
        
        all_packages = []
        
        for ecosystem_str in ecosystems:
            try:
                ecosystem = Ecosystem(ecosystem_str.lower())
            except ValueError:
                console.print(f"[red]Unknown ecosystem: {ecosystem_str}[/red]")
                continue
            
            if ecosystem not in self.sources:
                console.print(f"[yellow]Ecosystem {ecosystem_str} is disabled or not configured[/yellow]")
                continue
            
            # Get limit for this ecosystem
            ecosystem_limit = limit
            if ecosystem_limit is None:
                if ecosystem == Ecosystem.PYPI:
                    ecosystem_limit = self.policy.sources.pypi.fetch_limit
                elif ecosystem == Ecosystem.NPM:
                    ecosystem_limit = self.policy.sources.npm.fetch_limit
            
            with ProgressReporter(f"Fetching {ecosystem_str} packages"):
                try:
                    source = self.sources[ecosystem]
                    packages = source.fetch_with_fallback(ecosystem_limit)
                    
                    if packages:
                        # Save raw data
                        self._save_raw_data(packages, ecosystem_str, date)
                        all_packages.extend(packages)
                        
                        console.print(f"[green]Fetched {len(packages)} packages from {ecosystem_str}[/green]")
                    else:
                        console.print(f"[yellow]No packages fetched from {ecosystem_str}[/yellow]")
                        
                except Exception as e:
                    console.print(f"[red]Error fetching from {ecosystem_str}: {e}[/red]")
                    continue
        
        if all_packages:
            # Store in database
            self.storage.store_packages(all_packages, date)
            console.print(f"[green]Successfully fetched and stored {len(all_packages)} total packages[/green]")
        else:
            console.print("[yellow]No packages were fetched from any source[/yellow]")
        
        return all_packages
    
    def _save_raw_data(self, packages: List[PackageCandidate], ecosystem: str, date: str) -> None:
        """Save raw package data to JSONL files."""
        raw_dir = Path(f"data/raw/{date}")
        raw_dir.mkdir(parents=True, exist_ok=True)
        
        raw_file = raw_dir / f"{ecosystem}.jsonl"
        
        # Extract raw data from packages
        raw_data = []
        for package in packages:
            if package.raw_data:
                raw_data.append(package.raw_data)
        
        if raw_data:
            save_jsonl(raw_data, raw_file)
            console.print(f"[blue]Saved raw data to {raw_file}[/blue]")
    
    def get_available_ecosystems(self) -> List[str]:
        """Get list of available/enabled ecosystems."""
        return [ecosystem.value for ecosystem in self.sources.keys()]
    
    def get_ecosystem_status(self) -> Dict[str, dict]:
        """Get status of each ecosystem source."""
        status = {}
        
        for ecosystem_name in ['pypi', 'npm']:
            try:
                ecosystem = Ecosystem(ecosystem_name)
                config_key = ecosystem_name
                
                if ecosystem_name == 'pypi':
                    source_config = self.policy.sources.pypi
                else:
                    source_config = self.policy.sources.npm
                
                status[ecosystem_name] = {
                    'enabled': source_config.enabled,
                    'available': ecosystem in self.sources,
                    'fetch_limit': source_config.fetch_limit,
                    'timeout_seconds': source_config.timeout_seconds
                }
            except Exception as e:
                status[ecosystem_name] = {
                    'enabled': False,
                    'available': False,
                    'error': str(e)
                }
        
        return status