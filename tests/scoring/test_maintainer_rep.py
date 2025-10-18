"""Unit tests for maintainer reputation scoring."""

from datetime import UTC, datetime

import pytest

from radar.scoring.heuristics import PackageScorer
from radar.types import Ecosystem, PackageCandidate, PolicyConfig


@pytest.fixture
def policy():
    """Create a test policy configuration."""
    return PolicyConfig(
        weights={
            "name_suspicion": 0.30,
            "newness": 0.25,
            "repo_missing": 0.15,
            "maintainer_reputation": 0.15,
            "script_risk": 0.10,
            "version_flip": 0.03,
            "readme_plagiarism": 0.02,
        },
        heuristics={
            "new_package_days": 30,
            "suspicious_prefixes": [],
            "suspicious_suffixes": [],
            "canonical_packages": {"pypi": [], "npm": []},
            "fuzzy_threshold": 15,
            "thresholds": {
                "maintainer_age_days": 14,
                "readme_plagiarism": 0.85,
                "version_flip_dep_increase": 10,
            },
            "disposable_email_domains": [
                "mailinator",
                "10minutemail",
                "yopmail",
            ],
        },
        feed={},
        sources={},
        network={},
        storage={},
    )


def test_maintainer_reputation_single(policy):
    """Test maintainer reputation with single maintainer."""
    scorer = PackageScorer(policy)

    candidate = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test-package",
        version="1.0.0",
        created_at=datetime.now(UTC),
        maintainers_count=1,
    )

    score, reasons = scorer._score_maintainer_reputation(candidate)

    assert score == 1.0
    assert "Single maintainer" in reasons


def test_maintainer_reputation_disposable_email(policy):
    """Test maintainer reputation with disposable email."""
    scorer = PackageScorer(policy)

    candidate = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test-package",
        version="1.0.0",
        created_at=datetime.now(UTC),
        maintainers_count=1,
        disposable_email=True,
    )

    score, reasons = scorer._score_maintainer_reputation(candidate)

    assert score == 1.0
    assert any("Disposable email" in r for r in reasons)


def test_maintainer_reputation_young_account(policy):
    """Test maintainer reputation with young account."""
    scorer = PackageScorer(policy)

    candidate = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test-package",
        version="1.0.0",
        created_at=datetime.now(UTC),
        maintainers_count=1,
        maintainers_age_hint_days=7,  # Less than 14 day threshold
    )

    score, reasons = scorer._score_maintainer_reputation(candidate)

    assert score >= 1.0  # Should be at least base score + young account bonus
    assert any("young account" in r.lower() for r in reasons)


def test_maintainer_reputation_multiple_maintainers(policy):
    """Test maintainer reputation with multiple maintainers."""
    scorer = PackageScorer(policy)

    candidate = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test-package",
        version="1.0.0",
        created_at=datetime.now(UTC),
        maintainers_count=5,
    )

    score, reasons = scorer._score_maintainer_reputation(candidate)

    assert score == 0.0  # No concerns with 5 maintainers


def test_maintainer_reputation_two_maintainers(policy):
    """Test maintainer reputation with two maintainers."""
    scorer = PackageScorer(policy)

    candidate = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test-package",
        version="1.0.0",
        created_at=datetime.now(UTC),
        maintainers_count=2,
    )

    score, reasons = scorer._score_maintainer_reputation(candidate)

    assert score == 0.5
    assert "2 maintainers" in " ".join(reasons)


def test_maintainer_reputation_old_account(policy):
    """Test maintainer reputation with old account."""
    scorer = PackageScorer(policy)

    candidate = PackageCandidate(
        ecosystem=Ecosystem.NPM,
        name="test-package",
        version="1.0.0",
        created_at=datetime.now(UTC),
        maintainers_count=1,
        maintainers_age_hint_days=365,  # More than threshold
    )

    score, reasons = scorer._score_maintainer_reputation(candidate)

    assert score == 1.0  # Base score for single maintainer
    # Should not have young account warning
    assert not any("young" in r.lower() for r in reasons)

