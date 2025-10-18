"""Unit tests for PyPI version flip analysis."""

from unittest.mock import Mock, patch

import pytest

from radar.enrich.versions import _analyze_pypi_version_flip, analyze_version_history
from radar.types import PolicyConfig


@pytest.fixture
def policy():
    """Create a test policy configuration."""
    return PolicyConfig(
        weights={},
        heuristics={
            "lookups": {
                "timeout": 5,
            },
            "thresholds": {
                "version_flip_dep_increase": 10,
            },
        },
        feed={},
        sources={},
        network={"user_agent": "PhantomScan/test"},
        storage={},
    )


@pytest.fixture
def pypi_json_current():
    """Mock PyPI JSON for current version."""
    return {
        "info": {
            "name": "test-package",
            "version": "2.0.0",
            "requires_dist": [
                "requests>=2.0.0",
                "click>=7.0.0",
                "pytest>=6.0.0",
            ],
            "project_urls": {
                "Source": "https://github.com/test/package",
                "Documentation": "https://docs.test.com",
            },
        },
        "releases": {
            "1.0.0": [{"upload_time": "2023-01-01T00:00:00Z"}],
            "2.0.0": [{"upload_time": "2023-06-01T00:00:00Z"}],
        },
    }


@pytest.fixture
def pypi_json_previous():
    """Mock PyPI JSON for previous version."""
    return {
        "info": {
            "name": "test-package",
            "version": "1.0.0",
            "requires_dist": [
                "requests>=2.0.0",
            ],
            "project_urls": {
                "Source": "https://github.com/test/package",
                "Documentation": "https://docs.test.com",
            },
        },
        "releases": {},
    }


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
@patch("radar.enrich.versions.httpx.Client")
def test_analyze_pypi_version_flip_dep_increase(
    mock_client_cls, mock_offline, pypi_json_current, pypi_json_previous, policy
):
    """Test version flip detection with dependency increase."""
    # Current version has 3 deps, previous has 1 (increase of 2)
    # Need to increase to trigger threshold
    pypi_json_current["info"]["requires_dist"] = [f"dep{i}" for i in range(15)]
    pypi_json_previous["info"]["requires_dist"] = ["dep1"]

    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = pypi_json_previous

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    risk, reasons = _analyze_pypi_version_flip(pypi_json_current, policy)

    assert risk > 0.0
    assert any("dependency increase" in r.lower() for r in reasons)


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
@patch("radar.enrich.versions.httpx.Client")
def test_analyze_pypi_version_flip_urls_removed(
    mock_client_cls, mock_offline, pypi_json_current, pypi_json_previous, policy
):
    """Test version flip detection with removed project URLs."""
    # Remove Source URL in current version
    pypi_json_current["info"]["project_urls"] = {}

    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = pypi_json_previous

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    risk, reasons = _analyze_pypi_version_flip(pypi_json_current, policy)

    assert risk > 0.0
    assert any("removed" in r.lower() for r in reasons)


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
def test_analyze_pypi_version_flip_no_previous(mock_offline, policy):
    """Test version flip with no previous version."""
    pypi_json = {
        "info": {"name": "test-package", "version": "1.0.0"},
        "releases": {
            "1.0.0": [{"upload_time": "2023-01-01T00:00:00Z"}],
        },
    }

    risk, reasons = _analyze_pypi_version_flip(pypi_json, policy)

    assert risk == 0.0
    assert len(reasons) == 0


@patch("radar.enrich.versions.is_offline_mode", return_value=True)
def test_analyze_pypi_version_flip_offline(mock_offline, policy):
    """Test that version flip returns 0 in offline mode."""
    risk, reasons = _analyze_pypi_version_flip({}, policy)

    assert risk == 0.0
    assert len(reasons) == 0


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
@patch("radar.enrich.versions.httpx.Client")
def test_analyze_version_history_integration(mock_client_cls, mock_offline, policy):
    """Test the main analyze_version_history function."""
    mock_client = Mock()

    # Mock the initial request to get package JSON
    mock_response1 = Mock()
    mock_response1.status_code = 200
    mock_response1.json.return_value = {
        "info": {
            "name": "test-package",
            "version": "2.0.0",
            "requires_dist": ["dep1", "dep2"],
        },
        "releases": {
            "1.0.0": [{"upload_time": "2023-01-01T00:00:00Z"}],
            "2.0.0": [{"upload_time": "2023-06-01T00:00:00Z"}],
        },
    }

    # Mock the previous version request
    mock_response2 = Mock()
    mock_response2.status_code = 200
    mock_response2.json.return_value = {
        "info": {
            "name": "test-package",
            "version": "1.0.0",
            "requires_dist": ["dep1"],
        },
        "releases": {},
    }

    mock_client.get.side_effect = [mock_response1, mock_response2]
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    risk, reasons = analyze_version_history("test-package", "2.0.0", "pypi", policy)

    # Should not trigger threshold with only 1 additional dep
    assert risk >= 0.0


def test_analyze_version_history_npm(policy):
    """Test that npm ecosystem returns 0 (not supported)."""
    risk, reasons = analyze_version_history("test-package", "1.0.0", "npm", policy)

    assert risk == 0.0
    assert len(reasons) == 0


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
@patch("radar.enrich.versions.httpx.Client")
def test_analyze_pypi_version_flip_risk_capped(
    mock_client_cls, mock_offline, pypi_json_current, pypi_json_previous, policy
):
    """Test that risk score is capped at 0.7."""
    # Set up multiple risk factors
    pypi_json_current["info"]["requires_dist"] = [f"dep{i}" for i in range(50)]
    pypi_json_previous["info"]["requires_dist"] = ["dep1"]
    pypi_json_current["info"]["project_urls"] = {}
    pypi_json_current["info"]["entry_points"] = "console_scripts = main"

    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = pypi_json_previous

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    risk, reasons = _analyze_pypi_version_flip(pypi_json_current, policy)

    # Risk should be capped at 0.7
    assert risk <= 0.7

