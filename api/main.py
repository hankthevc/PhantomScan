"""FastAPI service for PhantomScan."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from radar.enrich.reputation import adjust_score_by_dependents, get_dependents_hint
from radar.enrich.versions import analyze_version_history
from radar.reports.casefile import generate_casefile
from radar.scoring.heuristics import PackageScorer
from radar.types import Ecosystem, PackageCandidate
from radar.utils import load_json, load_policy

app = FastAPI(
    title="PhantomScan API",
    description="Programmatic access to Phantom Dependency Radar",
    version="0.1.0",
)


class HealthResponse(BaseModel):
    """Health check response."""

    ok: bool
    version: str
    timestamp: str


class ScoreRequest(BaseModel):
    """Request to score a package."""

    ecosystem: str
    name: str
    version: str = "0.0.0"
    created_at: str | None = None
    homepage: str | None = None
    repository: str | None = None
    maintainers_count: int = 1
    has_install_scripts: bool = False


class ScoreResponse(BaseModel):
    """Response with score breakdown."""

    score: float
    breakdown: dict
    reasons: list[str]


class CasefileRequest(BaseModel):
    """Request to generate a casefile."""

    ecosystem: str
    name: str
    version: str = "0.0.0"
    score: float = 0.0
    created_at: str | None = None
    homepage: str | None = None
    repository: str | None = None
    maintainers_count: int = 1
    has_install_scripts: bool = False
    breakdown: dict | None = None
    reasons: list[str] = []


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        ok=True,
        version="0.1.0",
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/feed/{date}")
async def get_feed(date: str) -> JSONResponse:
    """Get feed for a specific date.

    Args:
        date: Date string in YYYY-MM-DD format

    Returns:
        JSON feed data
    """
    feed_path = Path("data/feeds") / date / "topN.json"

    if not feed_path.exists():
        raise HTTPException(status_code=404, detail=f"Feed not found for date: {date}")

    feed_data = load_json(feed_path)

    if feed_data is None:
        raise HTTPException(status_code=500, detail="Failed to load feed data")

    return JSONResponse(content=feed_data)


@app.get("/feed/latest")
async def get_latest_feed() -> JSONResponse:
    """Get the most recent feed.

    Returns:
        JSON feed data for the latest available date
    """
    feeds_dir = Path("data/feeds")

    if not feeds_dir.exists():
        raise HTTPException(status_code=404, detail="No feeds available")

    # Find latest date
    dates = []
    for date_dir in feeds_dir.iterdir():
        if date_dir.is_dir() and (date_dir / "topN.json").exists():
            dates.append(date_dir.name)

    if not dates:
        raise HTTPException(status_code=404, detail="No feeds available")

    latest_date = sorted(dates, reverse=True)[0]
    return await get_feed(latest_date)


@app.post("/score", response_model=ScoreResponse)
async def score_package(request: ScoreRequest) -> ScoreResponse:
    """Score a package using current policy.

    Args:
        request: Package metadata

    Returns:
        Score breakdown and reasons
    """
    async def _score_with_enrichment() -> ScoreResponse:
        try:
            # Parse ecosystem
            if request.ecosystem.lower() == "pypi":
                ecosystem = Ecosystem.PYPI
            elif request.ecosystem.lower() == "npm":
                ecosystem = Ecosystem.NPM
            else:
                raise HTTPException(status_code=400, detail=f"Invalid ecosystem: {request.ecosystem}")

            # Parse created_at
            if request.created_at:
                created_at = datetime.fromisoformat(request.created_at.replace("Z", "+00:00"))
            else:
                created_at = datetime.now(UTC)

            # Create candidate
            candidate = PackageCandidate(
                ecosystem=ecosystem,
                name=request.name,
                version=request.version,
                created_at=created_at,
                homepage=request.homepage,
                repository=request.repository,
                maintainers_count=request.maintainers_count,
                has_install_scripts=request.has_install_scripts,
            )

            # Score it
            policy = load_policy()
            scorer = PackageScorer(policy)

            breakdown = scorer.score(candidate)

            # Enrichment: Version flip analysis (PyPI only)
            if ecosystem == Ecosystem.PYPI:
                try:
                    version_flip_score, version_flip_reasons = analyze_version_history(
                        request.name,
                        request.version,
                        "pypi",
                        policy,
                    )
                    breakdown.version_flip = version_flip_score
                    breakdown.reasons.extend(version_flip_reasons)
                except Exception as e:
                    breakdown.reasons.append(f"Version analysis unavailable: {str(e)[:50]}")

            # Enrichment: Dependents count (optional)
            try:
                dependents_count = get_dependents_hint(
                    ecosystem.value,
                    request.name,
                    policy,
                )
                if dependents_count is not None:
                    _adjustment, dep_reasons = adjust_score_by_dependents(dependents_count, policy)
                    breakdown.reasons.extend(dep_reasons)
                    # Note: We don't apply adjustment to total score here, just informational
            except Exception:
                # Silent failure for optional enrichment
                pass

            total_score = scorer.compute_weighted_score(breakdown)

            return ScoreResponse(
                score=total_score,
                breakdown={
                    "name_suspicion": breakdown.name_suspicion,
                    "newness": breakdown.newness,
                    "repo_missing": breakdown.repo_missing,
                    "maintainer_reputation": breakdown.maintainer_reputation,
                    "script_risk": breakdown.script_risk,
                    "version_flip": breakdown.version_flip,
                    "readme_plagiarism": breakdown.readme_plagiarism,
                },
                reasons=breakdown.reasons,
            )

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Scoring failed: {e!s}") from e

    # Apply timeout to prevent long-running requests
    try:
        return await asyncio.wait_for(_score_with_enrichment(), timeout=8.0)
    except TimeoutError as e:
        raise HTTPException(
            status_code=503,
            detail="Scoring timeout - enrichment services may be overloaded"
        ) from e


@app.post("/casefile")
async def generate_casefile_endpoint(request: CasefileRequest) -> JSONResponse:
    """Generate a casefile for a package.

    Args:
        request: Package metadata

    Returns:
        Casefile metadata and content
    """
    try:
        # Build package data dict
        pkg_data = {
            "ecosystem": request.ecosystem,
            "name": request.name,
            "version": request.version,
            "score": request.score,
            "created_at": request.created_at or datetime.now(timezone.utc).isoformat(),
            "homepage": request.homepage,
            "repository": request.repository,
            "maintainers_count": request.maintainers_count,
            "has_install_scripts": request.has_install_scripts,
            "breakdown": request.breakdown or {},
            "reasons": request.reasons,
        }

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        output_path = generate_casefile(pkg_data, date_str)

        # Read generated content
        with open(output_path) as f:
            content = f.read()

        return JSONResponse(
            content={
                "success": True,
                "casefile_path": str(output_path),
                "content": content,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Casefile generation failed: {e!s}")


@app.get("/")
async def root() -> dict:
    """Root endpoint with API information."""
    return {
        "name": "PhantomScan API",
        "version": "0.1.0",
        "endpoints": {
            "health": "/health",
            "feed": "/feed/{date} or /feed/latest",
            "score": "POST /score",
            "casefile": "POST /casefile",
        },
        "docs": "/docs",
    }
