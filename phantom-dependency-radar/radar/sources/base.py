"""Base class for package data sources."""

import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx
from rich.console import Console

from ..types import Ecosystem, PackageCandidate
from ..utils import is_offline_mode, load_jsonl

console = Console()


class PackageSource(ABC):
    """Abstract base class for package data sources."""
    
    def __init__(self, ecosystem: Ecosystem, timeout: float = 30.0, retries: int = 3):
        self.ecosystem = ecosystem
        self.timeout = timeout
        self.retries = retries
        self._client: Optional[httpx.Client] = None
    
    @property
    def client(self) -> httpx.Client:
        """Get HTTP client instance."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self.timeout,
                headers={
                    "User-Agent": "PhantomDependencyRadar/0.1.0 (Security Research)"
                },
                follow_redirects=True
            )
        return self._client
    
    def __del__(self):
        """Clean up HTTP client."""
        if self._client is not None:
            self._client.close()
    
    @abstractmethod
    def fetch_recent_packages(self, limit: int = 200) -> List[PackageCandidate]:
        """
        Fetch recent packages from the source.
        
        Args:
            limit: Maximum number of packages to fetch
            
        Returns:
            List of PackageCandidate objects
        """
        pass
    
    @abstractmethod
    def get_offline_seed_path(self) -> str:
        """Get path to offline seed data file."""
        pass
    
    def fetch_with_fallback(self, limit: int = 200) -> List[PackageCandidate]:
        """
        Fetch packages with offline fallback.
        
        Args:
            limit: Maximum number of packages to fetch
            
        Returns:
            List of PackageCandidate objects
        """
        if is_offline_mode():
            return self._load_offline_seed(limit)
        
        try:
            return self.fetch_recent_packages(limit)
        except Exception as e:
            console.print(f"[red]Failed to fetch from {self.ecosystem.value}: {e}[/red]")
            console.print(f"[yellow]Falling back to offline seed data[/yellow]")
            return self._load_offline_seed(limit)
    
    def _load_offline_seed(self, limit: int = 200) -> List[PackageCandidate]:
        """Load packages from offline seed data."""
        seed_path = self.get_offline_seed_path()
        
        try:
            from pathlib import Path
            seed_data = load_jsonl(Path(seed_path))
            
            if not seed_data:
                console.print(f"[yellow]No seed data found at {seed_path}[/yellow]")
                return []
            
            packages = []
            for item in seed_data[:limit]:
                try:
                    package = self._parse_package_data(item)
                    if package:
                        packages.append(package)
                except Exception as e:
                    console.print(f"[yellow]Failed to parse seed package: {e}[/yellow]")
                    continue
            
            console.print(f"[green]Loaded {len(packages)} packages from offline seed[/green]")
            return packages
            
        except Exception as e:
            console.print(f"[red]Failed to load offline seed: {e}[/red]")
            return []
    
    @abstractmethod
    def _parse_package_data(self, raw_data: dict) -> Optional[PackageCandidate]:
        """
        Parse raw package data into PackageCandidate.
        
        Args:
            raw_data: Raw package data from API
            
        Returns:
            PackageCandidate object or None if parsing fails
        """
        pass
    
    def _retry_request(self, url: str, **kwargs) -> httpx.Response:
        """Make HTTP request with retries."""
        last_exception = None
        
        for attempt in range(self.retries):
            try:
                response = self.client.get(url, **kwargs)
                response.raise_for_status()
                return response
            except Exception as e:
                last_exception = e
                if attempt < self.retries - 1:
                    delay = 2 ** attempt  # Exponential backoff
                    console.print(f"[yellow]Request failed (attempt {attempt + 1}), retrying in {delay}s: {e}[/yellow]")
                    time.sleep(delay)
        
        raise last_exception or Exception("All retry attempts failed")
    
    def _safe_get(self, data: dict, key: str, default=None):
        """Safely get value from nested dict."""
        try:
            keys = key.split('.')
            value = data
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                elif isinstance(value, list) and k.isdigit():
                    idx = int(k)
                    value = value[idx] if 0 <= idx < len(value) else None
                else:
                    return default
                
                if value is None:
                    return default
            
            return value
        except (KeyError, IndexError, ValueError, TypeError):
            return default