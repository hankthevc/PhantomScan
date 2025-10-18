"""Tests for hallucination corpus matching."""

import tempfile
from pathlib import Path

import pytest
import yaml

from radar.corpus.hallucinations import is_known_hallucination, load_hallucinations


def test_load_hallucinations_default():
    """Test loading default hallucinations corpus."""
    exact, patterns = load_hallucinations()
    
    assert isinstance(exact, set)
    assert isinstance(patterns, list)
    assert len(exact) > 0  # Should have some exact matches
    assert len(patterns) > 0  # Should have some patterns


def test_load_hallucinations_custom():
    """Test loading custom hallucinations corpus."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(
            {
                "exact": ["fake-package", "test-hallucination"],
                "patterns": ["^fake-.*$", ".*-hallucinated$"],
            },
            f,
        )
        temp_file = Path(f.name)

    try:
        # Clear cache first
        import radar.corpus.hallucinations as hm
        hm._HALLUCINATIONS_CACHE = None
        
        exact, patterns = load_hallucinations(temp_file)
        
        assert "fake-package" in exact
        assert "test-hallucination" in exact
        assert len(patterns) == 2
    finally:
        temp_file.unlink()


def test_is_known_hallucination_exact():
    """Test exact match detection."""
    is_hallu, reason = is_known_hallucination("openai-python")
    assert is_hallu
    assert "Known hallucinated" in reason


def test_is_known_hallucination_case_insensitive():
    """Test case-insensitive matching."""
    is_hallu1, _ = is_known_hallucination("OPENAI-PYTHON")
    is_hallu2, _ = is_known_hallucination("OpenAI-Python")
    assert is_hallu1
    assert is_hallu2


def test_is_known_hallucination_pattern():
    """Test regex pattern matching."""
    is_hallu, reason = is_known_hallucination("openai-chat-sdk")
    assert is_hallu
    assert "pattern" in reason.lower()


def test_is_known_hallucination_negative():
    """Test that legitimate packages are not flagged."""
    is_hallu, _ = is_known_hallucination("requests")
    assert not is_hallu
    
    is_hallu, _ = is_known_hallucination("numpy")
    assert not is_hallu


def test_is_known_hallucination_with_custom_corpus():
    """Test detection with custom corpus."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(
            {
                "exact": ["my-fake-pkg"],
                "patterns": ["^custom-.*-test$"],
            },
            f,
        )
        temp_file = Path(f.name)

    try:
        # Clear cache
        import radar.corpus.hallucinations as hm
        hm._HALLUCINATIONS_CACHE = None
        
        is_hallu1, reason1 = is_known_hallucination("my-fake-pkg", temp_file)
        assert is_hallu1
        assert "Known hallucinated" in reason1
        
        is_hallu2, reason2 = is_known_hallucination("custom-something-test", temp_file)
        assert is_hallu2
        assert "pattern" in reason2.lower()
    finally:
        temp_file.unlink()


def test_load_hallucinations_missing_file():
    """Test graceful handling of missing file."""
    import radar.corpus.hallucinations as hm
    hm._HALLUCINATIONS_CACHE = None
    
    exact, patterns = load_hallucinations(Path("/nonexistent/file.yml"))
    assert exact == set()
    assert patterns == []


def test_load_hallucinations_invalid_pattern():
    """Test handling of invalid regex patterns."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(
            {
                "exact": ["valid-pkg"],
                "patterns": ["[invalid(regex", "^valid-.*$"],  # One invalid, one valid
            },
            f,
        )
        temp_file = Path(f.name)

    try:
        # Clear cache
        import radar.corpus.hallucinations as hm
        hm._HALLUCINATIONS_CACHE = None
        
        with pytest.warns(UserWarning):
            exact, patterns = load_hallucinations(temp_file)
        
        # Should still load the valid pattern
        assert len(patterns) == 1
        assert "valid-pkg" in exact
    finally:
        temp_file.unlink()
