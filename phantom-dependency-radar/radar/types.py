"""Core data types for the Phantom Dependency Radar."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class Ecosystem(str, Enum):
    """Supported package ecosystems."""
    PYPI = "pypi"
    NPM = "npm"


class PackageCandidate(BaseModel):
    """A package candidate from PyPI or npm."""
    
    name: str = Field(..., description="Package name")
    ecosystem: Ecosystem = Field(..., description="Package ecosystem (pypi/npm)")
    version: str = Field(..., description="Latest version")
    created_at: datetime = Field(..., description="Package creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    # Metadata
    description: Optional[str] = Field(None, description="Package description")
    author: Optional[str] = Field(None, description="Package author/maintainer")
    maintainers_count: int = Field(0, description="Number of maintainers")
    
    # Repository info
    repository_url: Optional[str] = Field(None, description="Repository URL")
    homepage_url: Optional[str] = Field(None, description="Homepage URL")
    
    # npm-specific
    has_install_scripts: bool = Field(False, description="Has npm install scripts")
    
    # Raw data for debugging
    raw_data: Dict[str, Any] = Field(default_factory=dict, description="Raw source data")
    
    @validator("name")
    def validate_name(cls, v: str) -> str:
        """Validate package name."""
        if not v or not v.strip():
            raise ValueError("Package name cannot be empty")
        return v.strip().lower()


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown for a package."""
    
    package_name: str = Field(..., description="Package name")
    ecosystem: Ecosystem = Field(..., description="Package ecosystem")
    
    # Individual scores (0.0 to 1.0)
    name_suspicion: float = Field(..., ge=0.0, le=1.0, description="Name suspicion score")
    newness: float = Field(..., ge=0.0, le=1.0, description="Package newness score")
    repo_missing: float = Field(..., ge=0.0, le=1.0, description="Repository missing score")
    maintainer_reputation: float = Field(..., ge=0.0, le=1.0, description="Maintainer reputation score")
    script_risk: float = Field(..., ge=0.0, le=1.0, description="Script risk score")
    
    # Weighted final score
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final weighted score")
    
    # Human-readable reasons
    reasons: List[str] = Field(default_factory=list, description="List of reasons for the score")
    
    # Scoring timestamp
    scored_at: datetime = Field(default_factory=datetime.utcnow, description="When the score was calculated")
    
    @validator("final_score")
    def validate_final_score(cls, v: float) -> float:
        """Ensure final score is reasonable."""
        return round(v, 3)


class ScoredCandidate(BaseModel):
    """A package candidate with its risk score."""
    
    candidate: PackageCandidate = Field(..., description="The package candidate")
    score: ScoreBreakdown = Field(..., description="Risk score breakdown")
    
    @property
    def name(self) -> str:
        """Get package name."""
        return self.candidate.name
    
    @property
    def ecosystem(self) -> Ecosystem:
        """Get package ecosystem."""
        return self.candidate.ecosystem
    
    @property
    def final_score(self) -> float:
        """Get final risk score."""
        return self.score.final_score


class FeedEntry(BaseModel):
    """Entry in the daily suspicious packages feed."""
    
    rank: int = Field(..., description="Rank in the feed (1-based)")
    name: str = Field(..., description="Package name")
    ecosystem: Ecosystem = Field(..., description="Package ecosystem")
    score: float = Field(..., ge=0.0, le=1.0, description="Risk score")
    created_at: datetime = Field(..., description="Package creation timestamp")
    
    # Quick access fields
    has_repository: bool = Field(..., description="Has repository URL")
    maintainers_count: int = Field(..., description="Number of maintainers")
    reasons: List[str] = Field(..., description="Risk reasons")
    
    # Links for investigation
    package_url: str = Field(..., description="Direct package URL")
    repository_url: Optional[str] = Field(None, description="Repository URL if available")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DailyFeed(BaseModel):
    """Daily feed of suspicious packages."""
    
    date: str = Field(..., description="Feed date (YYYY-MM-DD)")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    total_packages_analyzed: int = Field(..., description="Total packages analyzed")
    entries: List[FeedEntry] = Field(..., description="Top suspicious packages")
    
    class Config:
        """Pydantic config."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PolicyConfig(BaseModel):
    """Configuration loaded from policy.yml."""
    
    class SourceConfig(BaseModel):
        enabled: bool = True
        fetch_limit: int = 200
        timeout_seconds: int = 30
    
    class PyPIConfig(SourceConfig):
        rss_feeds: List[str] = Field(default_factory=list)
    
    class NPMConfig(SourceConfig):
        changes_feed: str = ""
    
    class Sources(BaseModel):
        pypi: PyPIConfig = Field(default_factory=PyPIConfig)
        npm: NPMConfig = Field(default_factory=NPMConfig)
    
    class ScoringWeights(BaseModel):
        name_suspicion: float = 0.30
        newness: float = 0.25
        repo_missing: float = 0.15
        maintainer_reputation: float = 0.15
        script_risk: float = 0.15
        
        @validator("*", pre=True)
        def validate_weights(cls, v: float) -> float:
            """Validate individual weights."""
            if not 0.0 <= v <= 1.0:
                raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
            return v
    
    class Scoring(BaseModel):
        weights: ScoringWeights = Field(default_factory=ScoringWeights)
        new_package_days: int = 30
        suspicious_prefixes: List[str] = Field(default_factory=list)
        suspicious_suffixes: List[str] = Field(default_factory=list)
        canonical_packages: Dict[str, List[str]] = Field(default_factory=dict)
    
    sources: Sources = Field(default_factory=Sources)
    scoring: Scoring = Field(default_factory=Scoring)
    
    @validator("scoring")
    def validate_scoring_weights_sum(cls, v: "PolicyConfig.Scoring") -> "PolicyConfig.Scoring":
        """Ensure scoring weights sum to 1.0."""
        weights = v.weights
        total = (
            weights.name_suspicion + 
            weights.newness + 
            weights.repo_missing + 
            weights.maintainer_reputation + 
            weights.script_risk
        )
        if abs(total - 1.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Scoring weights must sum to 1.0, got {total}")
        return v