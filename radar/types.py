"""Core data types for PhantomScan."""

from datetime import datetime
from enum import Enum
from typing import Optional

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
    homepage: Optional[str] = None
    repository: Optional[str] = None
    maintainers_count: int = 0
    has_install_scripts: bool = False  # npm only
    description: Optional[str] = None
    raw_metadata: dict = Field(default_factory=dict)


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown for a candidate."""

    name_suspicion: float = Field(ge=0.0, le=1.0)
    newness: float = Field(ge=0.0, le=1.0)
    repo_missing: float = Field(ge=0.0, le=1.0)
    maintainer_reputation: float = Field(ge=0.0, le=1.0)
    script_risk: float = Field(ge=0.0, le=1.0)
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
