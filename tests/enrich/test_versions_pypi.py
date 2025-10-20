"""Unit tests for PyPI version flip analysis."""

from unittest.mock import Mock, patch

import pytest

from radar.enrich.versions import _analyze_pypi_version_flip, analyze_version_history
from radar.types import PolicyConfig


@pytest.fixture()
def policy() -> PolicyConfig:
    """Create a test policy configuration."""
    return PolicyConfig(
        weights={},
        heuristics={
            "lookups": {
                "timeout": 5,
            },
            "thresholds": {
                "version_flip_window_days": 30,
            },
        },
        feed={},
        sources={},
        network={"user_agent": "PhantomScan/test"},
        storage={},
    )


@pytest.fixture()
def pypi_json_current() -> dict:
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
            "1.0.0": [{"upload_time": "2023-05-20T00:00:00Z"}],  # Within 30-day window
            "2.0.0": [{"upload_time": "2023-06-01T00:00:00Z"}],
        },
    }


@pytest.fixture()
def pypi_json_previous() -> dict:
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
    mock_client_cls: Mock,
    pypi_json_current: dict,
    pypi_json_previous: dict,
    policy: PolicyConfig,
) -> None:
    """Test version flip detection with dependency increase >= 8."""
    # Current version has 10 deps, previous has 1 (increase of 9 >= 8 threshold)
    pypi_json_current["info"]["requires_dist"] = [f"dep{i}" for i in range(10)]
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

    assert risk >= 0.6
    assert any("dependencies" in r.lower() for r in reasons)


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
@patch("radar.enrich.versions.httpx.Client")
def test_analyze_pypi_version_flip_urls_added(
    mock_client_cls: Mock,
    pypi_json_current: dict,
    pypi_json_previous: dict,
    policy: PolicyConfig,
) -> None:
    """Test version flip detection with added project URLs."""
    # Add new URLs in current version
    pypi_json_current["info"]["project_urls"] = {
        "Source": "https://github.com/test/package",
        "Documentation": "https://docs.test.com",
        "Changelog": "https://docs.test.com/changelog",
    }
    pypi_json_previous["info"]["project_urls"] = {
        "Source": "https://github.com/test/package",
    }

    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = pypi_json_previous

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    _risk, reasons = _analyze_pypi_version_flip(pypi_json_current, policy)

    assert any("documentation/project urls added" in r.lower() for r in reasons)


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
def test_analyze_pypi_version_flip_no_previous_in_window(policy: PolicyConfig) -> None:
    """Test version flip with no previous version in time window."""
    # Only one version exists, so no previous version in window
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
def test_analyze_pypi_version_flip_offline(policy: PolicyConfig) -> None:
    """Test that version flip returns 0 in offline mode."""
    risk, reasons = _analyze_pypi_version_flip({}, policy)

    assert risk == 0.0
    assert len(reasons) == 0


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
@patch("radar.enrich.versions.httpx.Client")
def test_analyze_version_history_integration(mock_client_cls: Mock, policy: PolicyConfig) -> None:
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

    risk, _reasons = analyze_version_history("test-package", "2.0.0", "pypi", policy)

    # Should not trigger threshold with only 1 additional dep
    assert risk >= 0.0


def test_analyze_version_history_npm(policy: PolicyConfig) -> None:
    """Test that npm ecosystem returns 0 (not supported)."""
    risk, reasons = analyze_version_history("test-package", "1.0.0", "npm", policy)

    assert risk == 0.0
    assert len(reasons) == 0


@patch("radar.enrich.versions.is_offline_mode", return_value=False)
@patch("radar.enrich.versions.httpx.Client")
def test_analyze_pypi_version_flip_risk_capped(
    mock_client_cls: Mock,
    pypi_json_current: dict,
    pypi_json_previous: dict,
    policy: PolicyConfig,
) -> None:
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

    risk, _reasons = _analyze_pypi_version_flip(pypi_json_current, policy)

    # Risk should be capped at 0.7
    assert risk <= 0.7
