"""Enrichment modules for PhantomScan."""

from radar.enrich.downloads import compute_download_anomaly, npm_weekly_downloads
from radar.enrich.provenance import npm_provenance_indicator, pypi_provenance_indicator
from radar.enrich.reputation import (
    compute_repo_asymmetry,
    get_dependents_hint,
    get_osv_facts,
    get_repo_facts,
)
from radar.enrich.versions import analyze_version_flip

__all__ = [
    "compute_download_anomaly",
    "npm_weekly_downloads",
    "npm_provenance_indicator",
    "pypi_provenance_indicator",
    "compute_repo_asymmetry",
    "get_dependents_hint",
    "get_osv_facts",
    "get_repo_facts",
    "analyze_version_flip",
]
