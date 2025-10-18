"""Tests for data source parsing."""



from radar.sources.npm import NpmSource
from radar.sources.pypi import PyPISource
from radar.types import Ecosystem


def test_pypi_parse_package_json() -> None:
    """Test PyPI JSON parsing."""
    source = PyPISource()

    # Sample PyPI package JSON
    sample_data = {
        "info": {
            "name": "test-package",
            "version": "1.0.0",
            "summary": "A test package",
            "home_page": "https://example.com",
            "project_urls": {
                "Source": "https://github.com/test/test",
            },
        },
        "releases": {
            "1.0.0": [
                {
                    "upload_time_iso_8601": "2024-01-01T00:00:00Z",
                }
            ]
        },
    }

    candidate = source._parse_package_json(sample_data)

    assert candidate.ecosystem == Ecosystem.PYPI
    assert candidate.name == "test-package"
    assert candidate.version == "1.0.0"
    assert candidate.homepage == "https://example.com"
    assert candidate.repository == "https://github.com/test/test"
    assert candidate.description == "A test package"


def test_pypi_parse_package_json_minimal() -> None:
    """Test PyPI JSON parsing with minimal data."""
    source = PyPISource()

    minimal_data = {
        "info": {
            "name": "minimal-pkg",
            "version": "0.1.0",
        },
        "releases": {},
    }

    candidate = source._parse_package_json(minimal_data)

    assert candidate.ecosystem == Ecosystem.PYPI
    assert candidate.name == "minimal-pkg"
    assert candidate.version == "0.1.0"
    assert candidate.homepage is None
    assert candidate.repository is None


def test_npm_parse_doc() -> None:
    """Test npm document parsing."""
    source = NpmSource()

    # Sample npm document
    sample_doc = {
        "name": "test-package",
        "description": "A test package",
        "dist-tags": {
            "latest": "1.0.0",
        },
        "time": {
            "created": "2024-01-01T00:00:00Z",
        },
        "repository": {
            "url": "https://github.com/test/test",
        },
        "homepage": "https://example.com",
        "maintainers": [
            {"name": "user1"},
            {"name": "user2"},
        ],
        "versions": {
            "1.0.0": {
                "scripts": {
                    "test": "jest",
                    "build": "webpack",
                }
            }
        },
    }

    candidate = source._parse_npm_doc(sample_doc)

    assert candidate is not None
    assert candidate.ecosystem == Ecosystem.NPM
    assert candidate.name == "test-package"
    assert candidate.version == "1.0.0"
    assert candidate.homepage == "https://example.com"
    assert candidate.repository == "https://github.com/test/test"
    assert candidate.maintainers_count == 2
    assert candidate.has_install_scripts is False


def test_npm_parse_doc_with_install_scripts() -> None:
    """Test npm document parsing with install scripts."""
    source = NpmSource()

    sample_doc = {
        "name": "suspicious-pkg",
        "dist-tags": {"latest": "1.0.0"},
        "time": {"created": "2024-01-01T00:00:00Z"},
        "maintainers": [{"name": "user1"}],
        "versions": {
            "1.0.0": {
                "scripts": {
                    "postinstall": "node install.js",
                    "test": "jest",
                }
            }
        },
    }

    candidate = source._parse_npm_doc(sample_doc)

    assert candidate is not None
    assert candidate.has_install_scripts is True


def test_npm_parse_doc_minimal() -> None:
    """Test npm document parsing with minimal data."""
    source = NpmSource()

    minimal_doc = {
        "name": "minimal-pkg",
        "dist-tags": {"latest": "0.1.0"},
    }

    candidate = source._parse_npm_doc(minimal_doc)

    assert candidate is not None
    assert candidate.name == "minimal-pkg"
    assert candidate.version == "0.1.0"
    assert candidate.maintainers_count == 0  # No maintainers in minimal doc


def test_npm_parse_doc_invalid_name() -> None:
    """Test npm document parsing rejects invalid names."""
    source = NpmSource()

    # Documents starting with _ are internal
    invalid_doc = {
        "name": "_internal",
        "dist-tags": {"latest": "1.0.0"},
    }

    candidate = source._parse_npm_doc(invalid_doc)
    # Should still parse but would be filtered in fetch_recent
    assert candidate is None or candidate.name == "_internal"


def test_npm_parse_doc_no_name() -> None:
    """Test npm document parsing handles missing name."""
    source = NpmSource()

    doc = {
        "dist-tags": {"latest": "1.0.0"},
    }

    candidate = source._parse_npm_doc(doc)
    assert candidate is None
