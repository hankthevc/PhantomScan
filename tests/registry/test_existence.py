"""Tests for registry existence checking."""

from unittest.mock import Mock, patch

import httpx
import pytest

from radar.registry.existence import exists_in_registry
from radar.types import PolicyConfig


@pytest.fixture
def policy() -> PolicyConfig:
    """Create a test policy configuration."""
    return PolicyConfig(
        weights={},
        heuristics={},
        feed={},
        sources={},
        network={"user_agent": "PhantomScan/test", "registry_timeout_seconds": 4},
        storage={},
    )


@patch("radar.registry.existence.httpx.Client")
def test_npm_exists_200(mock_client_cls: Mock, policy: PolicyConfig) -> None:
    """Test npm package exists (200 response)."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_client.head.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    exists, reason = exists_in_registry("npm", "express", policy)

    assert exists is True
    assert reason == "ok"


@patch("radar.registry.existence.httpx.Client")
def test_npm_not_found_404(mock_client_cls: Mock, policy: PolicyConfig) -> None:
    """Test npm package not found (404 response)."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 404
    mock_client.head.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    exists, reason = exists_in_registry("npm", "nonexistent-package-xyz", policy)

    assert exists is False
    assert reason == "404"


@patch("radar.registry.existence.httpx.Client")
def test_pypi_exists_200(mock_client_cls: Mock, policy: PolicyConfig) -> None:
    """Test PyPI package exists (200 response)."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    exists, reason = exists_in_registry("pypi", "requests", policy)

    assert exists is True
    assert reason == "ok"


@patch("radar.registry.existence.httpx.Client")
def test_pypi_not_found_404(mock_client_cls: Mock, policy: PolicyConfig) -> None:
    """Test PyPI package not found (404 response)."""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 404
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    exists, reason = exists_in_registry("pypi", "nonexistent-package-xyz", policy)

    assert exists is False
    assert reason == "404"


@patch("radar.registry.existence.httpx.Client")
def test_timeout(mock_client_cls: Mock, policy: PolicyConfig) -> None:
    """Test timeout handling."""
    mock_client = Mock()
    mock_client.head.side_effect = httpx.TimeoutException("Connection timeout")
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    exists, reason = exists_in_registry("npm", "test-pkg", policy)

    assert exists is False
    assert reason == "timeout"


@patch("radar.registry.existence.httpx.Client")
def test_network_error(mock_client_cls: Mock, policy: PolicyConfig) -> None:
    """Test network error handling."""
    mock_client = Mock()
    mock_client.head.side_effect = httpx.ConnectError("Connection refused")
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    exists, reason = exists_in_registry("npm", "test-pkg", policy)

    assert exists is False
    assert reason == "error"


@patch("radar.registry.existence.is_offline_mode", return_value=True)
def test_offline_mode(policy: PolicyConfig) -> None:
    """Test that offline mode returns False with offline reason."""
    exists, reason = exists_in_registry("npm", "express", policy)

    assert exists is False
    assert reason == "offline"


def test_unknown_ecosystem(policy: PolicyConfig) -> None:
    """Test unknown ecosystem returns error."""
    exists, reason = exists_in_registry("unknown", "test-pkg", policy)

    assert exists is False
    assert reason == "error"


@patch("radar.registry.existence.httpx.Client")
def test_npm_head_fallback_to_get(mock_client_cls: Mock, policy: PolicyConfig) -> None:
    """Test npm HEAD fails but GET succeeds."""
    mock_client = Mock()

    # HEAD returns 405, GET returns 200
    head_response = Mock()
    head_response.status_code = 405
    get_response = Mock()
    get_response.status_code = 200

    mock_client.head.return_value = head_response
    mock_client.get.return_value = get_response
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client_cls.return_value = mock_client

    exists, reason = exists_in_registry("npm", "express", policy)

    assert exists is True
    assert reason == "ok"
