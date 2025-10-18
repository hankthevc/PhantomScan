"""README plagiarism detection using n-gram Jaccard similarity."""



def _generate_ngrams(text: str, n: int = 5) -> set[str]:
    """Generate n-grams from text.
    
    Args:
        text: Input text
        n: N-gram size (default 5)
        
    Returns:
        Set of n-grams
    """
    # Normalize: lowercase and remove excessive whitespace
    text = " ".join(text.lower().split())

    if len(text) < n:
        return {text} if text else set()

    ngrams = set()
    for i in range(len(text) - n + 1):
        ngrams.add(text[i:i+n])

    return ngrams


def jaccard_similarity(set1: set[str], set2: set[str]) -> float:
    """Compute Jaccard similarity between two sets.
    
    Args:
        set1: First set
        set2: Second set
        
    Returns:
        Jaccard similarity (0.0 to 1.0)
    """
    if not set1 and not set2:
        return 0.0

    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union


def plagiarism_score(candidate_readme: str, repo_readme: str, n: int = 5) -> float:
    """Compute plagiarism score between two README texts.
    
    Uses n-gram Jaccard similarity.
    
    Args:
        candidate_readme: README from package distribution
        repo_readme: README from repository
        n: N-gram size (default 5)
        
    Returns:
        Similarity score (0.0 to 1.0), higher means more similar
    """
    if not candidate_readme or not repo_readme:
        return 0.0

    # Normalize whitespace first
    candidate_readme = " ".join(candidate_readme.split())
    repo_readme = " ".join(repo_readme.split())

    # Skip if texts are too short after normalization
    if len(candidate_readme) < n or len(repo_readme) < n:
        return 0.0

    ngrams1 = _generate_ngrams(candidate_readme, n)
    ngrams2 = _generate_ngrams(repo_readme, n)

    return jaccard_similarity(ngrams1, ngrams2)

