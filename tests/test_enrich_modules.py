"""Tests for enrichment modules."""

from datetime import datetime, timedelta, timezone

import pytest

from radar.enrich.downloads import compute_download_anomaly, npm_weekly_downloads
from radar.enrich.provenance import npm_provenance_indicator, pypi_provenance_indicator
from radar.enrich.reputation import compute_repo_asymmetry, get_dependents_hint, get_osv_facts, get_repo_facts
from radar.enrich.versions import analyze_version_flip


# Reputation tests
def test_get_repo_facts_no_url():
    """Test with no repository URL."""
    age, commits, topics, reasons = get_repo_facts(None)
    assert age is None
    assert commits == 0
    assert not topics


def test_get_repo_facts_non_github():
    """Test with non-GitHub URL."""
    age, commits, topics, reasons = get_repo_facts("https://gitlab.com/user/repo")
    assert age is None
    assert "Not a GitHub" in reasons[0]


def test_compute_repo_asymmetry_no_repo():
    """Test asymmetry with no repo age."""
    now = datetime.now(timezone.utc)
    score = compute_repo_asymmetry(now, None)
    assert score == 0.0


def test_compute_repo_asymmetry_aligned():
    """Test when package and repo ages are aligned."""
    now = datetime.now(timezone.utc)
    pkg_created = now - timedelta(days=30)
    repo_age = 30
    
    score = compute_repo_asymmetry(pkg_created, repo_age)
    assert score == 0.0  # Perfect alignment


def test_compute_repo_asymmetry_high():
    """Test high asymmetry."""
    now = datetime.now(timezone.utc)
    pkg_created = now - timedelta(days=10)  # Package is 10 days old
    repo_age = 365  # Repo is 1 year old
    
    score = compute_repo_asymmetry(pkg_created, repo_age)
    assert score > 0.5  # High asymmetry


def test_compute_repo_asymmetry_caps_at_one():
    """Test that asymmetry caps at 1.0."""
    now = datetime.now(timezone.utc)
    pkg_created = now - timedelta(days=1)
    repo_age = 1000  # Very old repo
    
    score = compute_repo_asymmetry(pkg_created, repo_age)
    assert score <= 1.0


def test_get_osv_facts_offline():
    """Test OSV in offline mode."""
    import os
    os.environ["RADAR_OFFLINE"] = "1"
    
    has_issues, reasons = get_osv_facts("npm", "test-package")
    assert not has_issues
    assert "Offline" in reasons[0]
    
    # Cleanup
    del os.environ["RADAR_OFFLINE"]


def test_get_dependents_hint():
    """Test dependents hint (placeholder)."""
    result = get_dependents_hint("npm", "react")
    # Currently returns None (not implemented)
    assert result is None


# Provenance tests
def test_npm_provenance_indicator_no_data():
    """Test with no packument."""
    score = npm_provenance_indicator({})
    assert score == 1.0  # No provenance


def test_npm_provenance_indicator_with_attestations():
    """Test with attestations field."""
    packument = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {
            "1.0.0": {
                "dist": {
                    "attestations": {"url": "https://registry.npmjs.org/..."}
                }
            }
        },
    }
    score = npm_provenance_indicator(packument)
    assert score == 0.0  # Has provenance


def test_npm_provenance_indicator_with_signatures():
    """Test with signatures field."""
    packument = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {
            "1.0.0": {
                "dist": {
                    "signatures": [{"keyid": "SHA256:jl3bwswu80PjjokCgh0o2w5c2U4LhQAE57gj9cz1kzA"}]
                }
            }
        },
    }
    score = npm_provenance_indicator(packument)
    assert score < 1.0  # Has some provenance


def test_npm_provenance_indicator_no_provenance():
    """Test without provenance."""
    packument = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {
            "1.0.0": {
                "dist": {}
            }
        },
    }
    score = npm_provenance_indicator(packument)
    assert score == 1.0


def test_pypi_provenance_indicator():
    """Test PyPI provenance (placeholder)."""
    score = pypi_provenance_indicator({})
    assert score == 1.0  # Currently always 1.0


# Downloads tests
def test_npm_weekly_downloads_offline():
    """Test downloads in offline mode."""
    import os
    os.environ["RADAR_OFFLINE"] = "1"
    
    downloads = npm_weekly_downloads("test-package")
    assert downloads is None
    
    # Cleanup
    del os.environ["RADAR_OFFLINE"]


def test_compute_download_anomaly_no_data():
    """Test with no download data."""
    score = compute_download_anomaly(None, 10)
    assert score == 0.0


def test_compute_download_anomaly_new_package_low_downloads():
    """Test new package with low downloads (normal)."""
    score = compute_download_anomaly(100, 3)
    assert score == 0.0


def test_compute_download_anomaly_new_package_high_downloads():
    """Test new package with high downloads (suspicious)."""
    score = compute_download_anomaly(5000, 2)
    assert score > 0.3  # Anomalous


def test_compute_download_anomaly_very_new_spike():
    """Test very new package with spike."""
    score = compute_download_anomaly(15000, 15)
    assert score > 0.5


def test_compute_download_anomaly_old_package():
    """Test old package (no flagging for now)."""
    score = compute_download_anomaly(50000, 365)
    assert score == 0.0  # Old packages not flagged


# Version flip tests
def test_analyze_version_flip_no_data():
    """Test with no packument."""
    risk, reasons = analyze_version_flip("npm", "test", None)
    assert risk == 0.0
    assert reasons == []


def test_analyze_version_flip_npm_no_scripts():
    """Test npm package with no install scripts."""
    packument = {
        "dist-tags": {"latest": "1.0.0"},
        "versions": {
            "1.0.0": {"scripts": {"test": "jest"}},
        },
        "time": {
            "1.0.0": "2024-01-01T00:00:00Z",
        },
    }
    risk, reasons = analyze_version_flip("npm", "test", packument)
    assert risk == 0.0


def test_analyze_version_flip_npm_with_flip():
    """Test npm version flip detection."""
    now = datetime.now(timezone.utc)
    prev_time = now - timedelta(days=10)
    
    packument = {
        "dist-tags": {"latest": "1.1.0"},
        "versions": {
            "1.0.0": {"scripts": {"test": "jest"}},  # No install scripts
            "1.1.0": {"scripts": {"postinstall": "node install.js"}},  # Added install script
        },
        "time": {
            "1.0.0": prev_time.isoformat().replace("+00:00", "Z"),
            "1.1.0": now.isoformat().replace("+00:00", "Z"),
        },
    }
    risk, reasons = analyze_version_flip("npm", "test", packument)
    assert risk > 0.5
    assert any("flip" in r.lower() for r in reasons)


def test_analyze_version_flip_npm_no_flip():
    """Test npm with install scripts in both versions."""
    now = datetime.now(timezone.utc)
    prev_time = now - timedelta(days=10)
    
    packument = {
        "dist-tags": {"latest": "1.1.0"},
        "versions": {
            "1.0.0": {"scripts": {"postinstall": "node setup.js"}},
            "1.1.0": {"scripts": {"postinstall": "node install.js"}},
        },
        "time": {
            "1.0.0": prev_time.isoformat().replace("+00:00", "Z"),
            "1.1.0": now.isoformat().replace("+00:00", "Z"),
        },
    }
    risk, reasons = analyze_version_flip("npm", "test", packument)
    assert risk == 0.0  # No flip (both have install scripts)


def test_analyze_version_flip_pypi():
    """Test PyPI version flip (placeholder)."""
    info_json = {
        "info": {"version": "1.0.0"},
        "releases": {
            "1.0.0": [{"upload_time_iso_8601": "2024-01-01T00:00:00Z"}],
        },
    }
    risk, reasons = analyze_version_flip("pypi", "test", info_json)
    assert risk == 0.0  # Currently placeholder
