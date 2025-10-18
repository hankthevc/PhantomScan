"""Unit tests for dependents enrichment."""

import os
from unittest.mock import Mock, patch

import pytest

from radar.enrich.reputation import (
    adjust_score_by_dependents,
    get_dependents_hint,
)
from radar.types import PolicyConfig


@pytest.fixture
def policy():
    """Create a test policy configuration."""
    return PolicyConfig(
        weights={},
        heuristics={
            "lookups": {
                "enable_dependents": True,
                "libraries_io_api": "https://libraries.io/api",
                "timeout": 5,
                "dependents_low_threshold": 0,
                "dependents_high_threshold": 50,
            },
        },
        feed={},
        sources={},
        network={},
        storage={},
    )


@patch.dict(os.environ, {"LIBRARIES_IO_KEY": "test_key"})
@patch("radar.enrich.reputation.httpx.Client")
def test_get_dependents_hint_success(mock_client_cls, policy):
    """Test successful dependents lookup."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"X-Total": "42"}
    mock_response.json.return_value = []

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    count = get_dependents_hint("pypi", "test-package", policy)

    assert count == 42


@patch.dict(os.environ, {"LIBRARIES_IO_KEY": "test_key"})
@patch("radar.enrich.reputation.httpx.Client")
def test_get_dependents_hint_not_found(mock_client_cls, policy):
    """Test dependents lookup for non-existent package."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 404

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    count = get_dependents_hint("pypi", "nonexistent-package", policy)

    assert count == 0


@patch.dict(os.environ, {}, clear=True)
def test_get_dependents_hint_no_api_key(policy):
    """Test that lookup returns None without API key."""
    count = get_dependents_hint("pypi", "test-package", policy)

    assert count is None


def test_get_dependents_hint_disabled(policy):
    """Test that lookup returns None when disabled."""
    policy.heuristics["lookups"]["enable_dependents"] = False

    count = get_dependents_hint("pypi", "test-package", policy)

    assert count is None


@patch.dict(os.environ, {"LIBRARIES_IO_KEY": "test_key"})
@patch("radar.enrich.reputation.httpx.Client")
def test_get_dependents_hint_fallback_to_list(mock_client_cls, policy):
    """Test fallback to counting list items when X-Total header is missing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {}
    mock_response.json.return_value = [{"name": "pkg1"}, {"name": "pkg2"}]

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    count = get_dependents_hint("pypi", "test-package", policy)

    assert count == 2


def test_adjust_score_by_dependents_none(policy):
    """Test adjustment with None dependents count."""
    adjustment, reasons = adjust_score_by_dependents(None, policy)

    assert adjustment == 1.0
    assert len(reasons) == 0


def test_adjust_score_by_dependents_zero(policy):
    """Test adjustment with zero dependents."""
    adjustment, reasons = adjust_score_by_dependents(0, policy)

    assert adjustment == 1.0
    assert "No known dependents" in reasons[0]


def test_adjust_score_by_dependents_high(policy):
    """Test adjustment with high dependents count."""
    adjustment, reasons = adjust_score_by_dependents(100, policy)

    assert adjustment == 0.7
    assert "Established package" in reasons[0]


def test_adjust_score_by_dependents_moderate(policy):
    """Test adjustment with moderate dependents count."""
    adjustment, reasons = adjust_score_by_dependents(25, policy)

    assert adjustment == 0.85
    assert "25 dependents" in reasons[0]


@patch.dict(os.environ, {"LIBRARIES_IO_KEY": "test_key"})
@patch("radar.enrich.reputation.httpx.Client")
def test_get_dependents_hint_npm(mock_client_cls, policy):
    """Test dependents lookup for npm package."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.headers = {"X-Total": "150"}
    mock_response.json.return_value = []

    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    count = get_dependents_hint("npm", "express", policy)

    assert count == 150

    # Verify the correct ecosystem mapping was used
    call_args = mock_client.get.call_args
    assert "NPM/express" in call_args[0][0]

