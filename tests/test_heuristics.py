"""Tests for scoring heuristics."""

from datetime import datetime, timedelta, timezone

import pytest

from radar.scoring.heuristics import PackageScorer
from radar.types import Ecosystem, PackageCandidate
from radar.utils import load_policy


@pytest.fixture
def scorer() -> PackageScorer:
    """Create a scorer with default policy."""
    policy = load_policy()
    return PackageScorer(policy)


@pytest.fixture
def benign_package() -> PackageCandidate:
    """Create a benign package candidate."""
    return PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="legitimate-package",
        version="1.0.0",
        created_at=datetime.now(timezone.utc) - timedelta(days=365),
        homepage="https://example.com",
        repository="https://github.com/org/repo",
        maintainers_count=5,
        has_install_scripts=False,
    )


@pytest.fixture
def suspicious_package() -> PackageCandidate:
    """Create a suspicious package candidate."""
    return PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="requests2",  # Similar to 'requests'
        version="0.0.1",
        created_at=datetime.now(timezone.utc),  # Brand new
        homepage=None,
        repository=None,
        maintainers_count=1,
        has_install_scripts=False,
    )


def test_score_benign_package(scorer: PackageScorer, benign_package: PackageCandidate) -> None:
    """Test scoring of a benign package."""
    breakdown = scorer.score(benign_package)
    total_score = scorer.compute_weighted_score(breakdown)

    # Should have low score
    assert total_score < 0.3

    # Name should not be suspicious
    assert breakdown.name_suspicion < 0.5

    # Not new
    assert breakdown.newness == 0.0

    # Has repo
    assert breakdown.repo_missing == 0.0

    # Multiple maintainers
    assert breakdown.maintainer_reputation == 0.0


def test_score_suspicious_package(
    scorer: PackageScorer, suspicious_package: PackageCandidate
) -> None:
    """Test scoring of a suspicious package."""
    breakdown = scorer.score(suspicious_package)
    total_score = scorer.compute_weighted_score(breakdown)

    # Should have high score
    assert total_score > 0.5

    # Name is suspicious (similar to 'requests')
    assert breakdown.name_suspicion > 0.5

    # Brand new
    assert breakdown.newness == 1.0

    # No repo/homepage
    assert breakdown.repo_missing == 1.0

    # Single maintainer
    assert breakdown.maintainer_reputation == 1.0

    # Should have reasons
    assert len(breakdown.reasons) > 0


def test_name_suspicion_prefix(scorer: PackageScorer) -> None:
    """Test name suspicion with brand prefix."""
    package = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="openai-tools",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(package)

    # Should flag brand prefix
    assert breakdown.name_suspicion >= 0.6
    assert any("openai" in reason.lower() for reason in breakdown.reasons)


def test_name_suspicion_suffix(scorer: PackageScorer) -> None:
    """Test name suspicion with trope suffix."""
    package = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="somepkg-cli",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(package)

    # Should flag suffix
    assert breakdown.name_suspicion >= 0.5
    assert any("-cli" in reason.lower() for reason in breakdown.reasons)


def test_name_suspicion_fuzzy_match(scorer: PackageScorer) -> None:
    """Test name suspicion with fuzzy matching."""
    package = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="requestz",  # Very similar to 'requests'
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(package)

    # Should detect similarity
    assert breakdown.name_suspicion > 0.3
    # May or may not have a specific reason depending on threshold


def test_newness_scoring(scorer: PackageScorer) -> None:
    """Test newness scoring."""
    # Brand new package
    new_pkg = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown_new = scorer.score(new_pkg)
    assert breakdown_new.newness == 1.0

    # Old package
    old_pkg = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc) - timedelta(days=365),
        maintainers_count=1,
    )

    breakdown_old = scorer.score(old_pkg)
    assert breakdown_old.newness == 0.0


def test_repo_missing_scoring(scorer: PackageScorer) -> None:
    """Test repo missing scoring."""
    # No repo or homepage
    no_repo = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(no_repo)
    assert breakdown.repo_missing == 1.0

    # Has both
    has_both = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        homepage="https://example.com",
        repository="https://github.com/test/test",
        maintainers_count=1,
    )

    breakdown_both = scorer.score(has_both)
    assert breakdown_both.repo_missing == 0.0


def test_maintainer_reputation_scoring(scorer: PackageScorer) -> None:
    """Test maintainer reputation scoring."""
    # Single maintainer
    single = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(single)
    assert breakdown.maintainer_reputation == 1.0

    # Two maintainers
    two = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=2,
    )

    breakdown_two = scorer.score(two)
    assert breakdown_two.maintainer_reputation == 0.5

    # Many maintainers
    many = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=5,
    )

    breakdown_many = scorer.score(many)
    assert breakdown_many.maintainer_reputation == 0.0


def test_script_risk_npm(scorer: PackageScorer) -> None:
    """Test script risk scoring for npm packages."""
    # npm with install scripts
    with_scripts = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
        has_install_scripts=True,
    )

    breakdown = scorer.score(with_scripts)
    assert breakdown.script_risk == 1.0

    # npm without install scripts
    without_scripts = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
        has_install_scripts=False,
    )

    breakdown_no_scripts = scorer.score(without_scripts)
    assert breakdown_no_scripts.script_risk == 0.0


def test_script_risk_pypi(scorer: PackageScorer) -> None:
    """Test script risk scoring for PyPI packages (always 0)."""
    pypi_pkg = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(pypi_pkg)
    assert breakdown.script_risk == 0.0


def test_weighted_score_calculation(scorer: PackageScorer) -> None:
    """Test that weighted score is calculated correctly."""
    package = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="test",
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(package)
    weighted = scorer.compute_weighted_score(breakdown)

    # Manually calculate
    expected = (
        breakdown.name_suspicion * scorer.weights["name_suspicion"]
        + breakdown.newness * scorer.weights["newness"]
        + breakdown.repo_missing * scorer.weights["repo_missing"]
        + breakdown.maintainer_reputation * scorer.weights["maintainer_reputation"]
        + breakdown.script_risk * scorer.weights["script_risk"]
    )

    assert abs(weighted - expected) < 0.001

    # Score should be in [0, 1]
    assert 0.0 <= weighted <= 1.0
