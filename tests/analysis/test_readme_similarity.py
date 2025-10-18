"""Unit tests for readme similarity analysis."""


from radar.analysis.readme_similarity import (
    _generate_ngrams,
    jaccard_similarity,
    plagiarism_score,
)


def test_generate_ngrams_basic():
    """Test basic n-gram generation."""
    text = "hello world"
    ngrams = _generate_ngrams(text, n=3)

    assert "hel" in ngrams
    assert "ell" in ngrams
    assert "llo" in ngrams
    assert "lo " in ngrams
    assert "o w" in ngrams
    assert "wor" in ngrams
    assert "orl" in ngrams
    assert "rld" in ngrams


def test_generate_ngrams_short_text():
    """Test n-gram generation with text shorter than n."""
    text = "hi"
    ngrams = _generate_ngrams(text, n=5)

    assert ngrams == {"hi"}


def test_generate_ngrams_normalization():
    """Test that text is normalized (lowercased, whitespace stripped)."""
    text = "  Hello   WORLD  "
    ngrams = _generate_ngrams(text, n=3)

    # Should be normalized to "hello world"
    assert "hel" in ngrams
    assert "HEL" not in ngrams


def test_jaccard_similarity_identical():
    """Test Jaccard similarity with identical sets."""
    set1 = {"a", "b", "c"}
    set2 = {"a", "b", "c"}

    similarity = jaccard_similarity(set1, set2)
    assert similarity == 1.0


def test_jaccard_similarity_disjoint():
    """Test Jaccard similarity with disjoint sets."""
    set1 = {"a", "b", "c"}
    set2 = {"d", "e", "f"}

    similarity = jaccard_similarity(set1, set2)
    assert similarity == 0.0


def test_jaccard_similarity_partial():
    """Test Jaccard similarity with partial overlap."""
    set1 = {"a", "b", "c", "d"}
    set2 = {"c", "d", "e", "f"}

    # Intersection: {c, d} = 2, Union: {a, b, c, d, e, f} = 6
    similarity = jaccard_similarity(set1, set2)
    assert abs(similarity - 0.333) < 0.01


def test_jaccard_similarity_empty():
    """Test Jaccard similarity with empty sets."""
    similarity = jaccard_similarity(set(), set())
    assert similarity == 0.0


def test_plagiarism_score_identical():
    """Test plagiarism score with identical texts."""
    text1 = "This is a test document with some content that is long enough"
    text2 = "This is a test document with some content that is long enough"

    score = plagiarism_score(text1, text2, n=5)
    assert score == 1.0


def test_plagiarism_score_different():
    """Test plagiarism score with completely different texts."""
    text1 = "The quick brown fox jumps over the lazy dog"
    text2 = "Alice was beginning to get very tired of sitting by her sister"

    score = plagiarism_score(text1, text2, n=5)
    assert score < 0.2  # Should be very low


def test_plagiarism_score_similar():
    """Test plagiarism score with similar texts."""
    text1 = "This package provides utilities for data processing and analysis"
    text2 = "This package provides tools for data processing and analytics"

    score = plagiarism_score(text1, text2, n=5)
    assert 0.4 < score < 1.0  # Should be moderately high


def test_plagiarism_score_empty():
    """Test plagiarism score with empty texts."""
    score = plagiarism_score("", "some text", n=5)
    assert score == 0.0

    score = plagiarism_score("some text", "", n=5)
    assert score == 0.0


def test_plagiarism_score_too_short():
    """Test plagiarism score with texts too short."""
    text1 = "short"
    text2 = "text"

    score = plagiarism_score(text1, text2, n=5)
    assert score == 0.0


def test_plagiarism_score_case_insensitive():
    """Test that plagiarism score is case-insensitive."""
    text1 = "THIS IS A TEST WITH ENOUGH TEXT"
    text2 = "this is a test with enough text"

    score = plagiarism_score(text1, text2, n=5)
    assert score == 1.0

