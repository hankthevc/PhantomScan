"""Core data types for PhantomScan."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Ecosystem(str, Enum):
    """Package ecosystem identifier."""

    PYPI = "pypi"
    NPM = "npm"


class PackageCandidate(BaseModel):
    """Normalized package candidate from any ecosystem."""

    ecosystem: Ecosystem
    name: str
    version: str
    created_at: datetime
    homepage: str | None = None
    repository: str | None = None
    maintainers_count: int = 0
    has_install_scripts: bool = False  # npm only
    description: str | None = None
    raw_metadata: dict = Field(default_factory=dict)
    # Enhanced maintainer signals
    disposable_email: bool = False
    maintainers_age_hint_days: int | None = None


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown for a candidate."""

    name_suspicion: float = Field(ge=0.0, le=1.0)
    newness: float = Field(ge=0.0, le=1.0)
    repo_missing: float = Field(ge=0.0, le=1.0)
    maintainer_reputation: float = Field(ge=0.0, le=1.0)
    script_risk: float = Field(ge=0.0, le=1.0)
    version_flip: float = Field(ge=0.0, le=1.0, default=0.0)
    readme_plagiarism: float = Field(ge=0.0, le=1.0, default=0.0)
    reasons: list[str] = Field(default_factory=list)


class ScoredCandidate(BaseModel):
    """Package candidate with computed risk score."""

    candidate: PackageCandidate
    score: float = Field(ge=0.0, le=1.0)
    breakdown: ScoreBreakdown
    scored_at: datetime = Field(default_factory=datetime.utcnow)


class PolicyConfig(BaseModel):
    """Policy configuration for scoring and operations."""

    weights: dict[str, float]
    heuristics: dict
    feed: dict
    sources: dict
    network: dict
    storage: dict
