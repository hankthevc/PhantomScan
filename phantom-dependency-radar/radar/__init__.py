"""
Phantom Dependency Radar - A slopsquatting monitor for PyPI and npm.

This package provides tools for detecting potentially malicious packages
that may be attempting to exploit typos in popular package names.
"""

__version__ = "0.1.0"
__author__ = "Security Team"

from .types import PackageCandidate, ScoreBreakdown

__all__ = ["PackageCandidate", "ScoreBreakdown"]