"""Base class for package data sources."""

from abc import ABC, abstractmethod

from radar.types import Ecosystem, PackageCandidate


class PackageSource(ABC):
    """Abstract base class for package registry sources."""

    @abstractmethod
    def fetch_recent(self, limit: int = 400) -> list[PackageCandidate]:
        """Fetch recently published or updated packages.

        Args:
            limit: Maximum number of packages to fetch

        Returns:
            List of normalized package candidates
        """
        pass

    @property
    @abstractmethod
    def ecosystem(self) -> Ecosystem:
        """Return the ecosystem identifier."""
        pass
