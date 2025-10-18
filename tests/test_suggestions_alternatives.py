"""Tests for safer alternatives suggestions."""

import pytest

from radar.suggestions.alternatives import get_distance_description, suggest_alternatives
from radar.types import Ecosystem


def test_suggest_alternatives_empty_name():
    """Test with empty name."""
    results = suggest_alternatives("", Ecosystem.NPM, ["react", "vue"])
    assert results == []


def test_suggest_alternatives_empty_canonical():
    """Test with empty canonical list."""
    results = suggest_alternatives("test-pkg", Ecosystem.NPM, [])
    assert results == []


def test_suggest_alternatives_close_match():
    """Test with close typosquatting match."""
    canonical = ["requests", "urllib3", "httpx"]
    results = suggest_alternatives("reqeusts", Ecosystem.PYPI, canonical)
    
    assert len(results) > 0
    assert results[0][0] == "requests"  # Should match 'requests'
    assert results[0][1] >= 85  # High similarity


def test_suggest_alternatives_substring():
    """Test with substring/prefix match."""
    canonical = ["react", "react-dom", "react-router"]
    results = suggest_alternatives("react-native-x", Ecosystem.NPM, canonical)
    
    # Should find react-related packages
    assert len(results) > 0
    assert any("react" in alt[0] for alt in results)


def test_suggest_alternatives_threshold():
    """Test threshold filtering."""
    canonical = ["pandas", "numpy", "scipy"]
    
    # Low threshold - should find matches
    results_low = suggest_alternatives("pandaz", Ecosystem.PYPI, canonical, threshold=80)
    assert len(results_low) > 0
    
    # High threshold - should find fewer/no matches
    results_high = suggest_alternatives("pandaz", Ecosystem.PYPI, canonical, threshold=98)
    assert len(results_high) <= len(results_low)


def test_suggest_alternatives_no_exact_match():
    """Test that exact matches are excluded."""
    canonical = ["requests", "httpx"]
    results = suggest_alternatives("requests", Ecosystem.PYPI, canonical)
    
    # Should not include exact match
    assert all(alt[0] != "requests" for alt in results)


def test_suggest_alternatives_sorted():
    """Test that results are sorted by similarity."""
    canonical = ["react", "reactjs", "reactor"]
    results = suggest_alternatives("reakt", Ecosystem.NPM, canonical)
    
    if len(results) > 1:
        # Check descending order
        for i in range(len(results) - 1):
            assert results[i][1] >= results[i + 1][1]


def test_suggest_alternatives_limit():
    """Test that results are limited to top 5."""
    # Create many similar canonical packages
    canonical = [f"test-package-{i}" for i in range(20)]
    results = suggest_alternatives("test-packag", Ecosystem.NPM, canonical)
    
    assert len(results) <= 5


def test_suggest_alternatives_case_insensitive():
    """Test case-insensitive matching."""
    canonical = ["Express", "Lodash", "Axios"]
    results = suggest_alternatives("EXPRESS", Ecosystem.NPM, canonical)
    
    assert len(results) > 0
    assert any(alt[0].lower() == "express" for alt in results)


def test_suggest_alternatives_with_ecosystem_string():
    """Test with ecosystem as string."""
    canonical = ["requests"]
    results = suggest_alternatives("requets", "pypi", canonical)
    
    assert len(results) > 0


def test_suggest_alternatives_typo_detection():
    """Test various typosquatting patterns."""
    canonical = ["numpy"]
    
    # Character swap
    results1 = suggest_alternatives("nupmy", Ecosystem.PYPI, canonical)
    assert len(results1) > 0
    
    # Missing character
    results2 = suggest_alternatives("numy", Ecosystem.PYPI, canonical)
    assert len(results2) > 0
    
    # Extra character
    results3 = suggest_alternatives("numpyy", Ecosystem.PYPI, canonical)
    assert len(results3) > 0


def test_get_distance_description():
    """Test distance description helper."""
    assert "very similar" in get_distance_description(97)
    assert "similar" in get_distance_description(92)
    assert "somewhat similar" in get_distance_description(87)
    assert "moderately similar" in get_distance_description(82)


def test_suggest_alternatives_npm_canonical():
    """Test with real npm canonical packages."""
    canonical = ["react", "vue", "angular", "express", "lodash"]
    
    # Test lodash typo
    results = suggest_alternatives("lodsh", Ecosystem.NPM, canonical)
    assert len(results) > 0
    assert results[0][0] == "lodash"


def test_suggest_alternatives_pypi_canonical():
    """Test with real PyPI canonical packages."""
    canonical = ["requests", "numpy", "pandas", "flask", "django"]
    
    # Test flask typo
    results = suggest_alternatives("flsk", Ecosystem.PYPI, canonical)
    assert len(results) > 0
    assert results[0][0] == "flask"


def test_suggest_alternatives_no_similar():
    """Test with completely different name."""
    canonical = ["react", "vue", "angular"]
    results = suggest_alternatives("zzz-completely-different-xyz", Ecosystem.NPM, canonical, threshold=92)
    
    # Should find no matches above threshold
    assert len(results) == 0
