"""Heuristic-based scoring for package candidates."""

from datetime import datetime, timezone
from pathlib import Path

from rapidfuzz import fuzz

from radar.analysis.npm_scripts import lint_scripts
from radar.analysis.pypi_artifacts import (
    cleanup_tempdir,
    compare_sdist_wheel,
    download_and_unpack,
    fetch_latest_release_files,
    static_scan,
)
from radar.corpus.hallucinations import is_known_hallucination
from radar.enrich.downloads import compute_download_anomaly, npm_weekly_downloads
from radar.enrich.provenance import npm_provenance_indicator, pypi_provenance_indicator
from radar.enrich.reputation import compute_repo_asymmetry, get_osv_facts, get_repo_facts
from radar.enrich.versions import analyze_version_flip
from radar.types import Ecosystem, PackageCandidate, ScoreBreakdown, PolicyConfig
from radar.utils import is_offline_mode


class PackageScorer:
    """Compute risk scores for package candidates."""

    def __init__(self, policy: PolicyConfig) -> None:
        """Initialize scorer with policy configuration."""
        self.policy = policy
        self.weights = policy.weights
        self.heuristics = policy.heuristics

    def score(self, candidate: PackageCandidate) -> ScoreBreakdown:
        """Compute risk score breakdown for a candidate."""
        reasons = []

        # 1. Name suspicion
        name_score, name_reasons = self._score_name_suspicion(candidate)
        reasons.extend(name_reasons)

        # 2. Known hallucination
        hallu_score, hallu_reasons = self._score_known_hallucination(candidate)
        reasons.extend(hallu_reasons)

        # 3. Content risk (npm scripts OR PyPI artifacts)
        content_score, content_reasons = self._score_content_risk(candidate)
        reasons.extend(content_reasons)

        # 4. Script risk (npm only, legacy subscore)
        script_score, script_reasons = self._score_script_risk(candidate)
        reasons.extend(script_reasons)

        # 5. Newness
        newness_score, newness_reasons = self._score_newness(candidate)
        reasons.extend(newness_reasons)

        # 6. Repository missing
        repo_score, repo_reasons = self._score_repo_missing(candidate)
        reasons.extend(repo_reasons)

        # 7. Maintainer reputation
        maint_score, maint_reasons = self._score_maintainer_reputation(candidate)
        reasons.extend(maint_reasons)

        # 8. Documentation absence
        docs_score, docs_reasons = self._score_docs_absence(candidate)
        reasons.extend(docs_reasons)

        # 9. Provenance risk
        prov_score, prov_reasons = self._score_provenance_risk(candidate)
        reasons.extend(prov_reasons)

        # 10. Repository asymmetry
        asym_score, asym_reasons = self._score_repo_asymmetry(candidate)
        reasons.extend(asym_reasons)

        # 11. Download anomaly
        dl_score, dl_reasons = self._score_download_anomaly(candidate)
        reasons.extend(dl_reasons)

        # 12. Version flip
        vflip_score, vflip_reasons = self._score_version_flip(candidate)
        reasons.extend(vflip_reasons)

        return ScoreBreakdown(
            name_suspicion=name_score,
            known_hallucination=hallu_score,
            content_risk=content_score,
            script_risk=script_score,
            newness=newness_score,
            repo_missing=repo_score,
            maintainer_reputation=maint_score,
            docs_absence=docs_score,
            provenance_risk=prov_score,
            repo_asymmetry=asym_score,
            download_anomaly=dl_score,
            version_flip=vflip_score,
            reasons=reasons,
        )

    def compute_weighted_score(self, breakdown: ScoreBreakdown) -> float:
        """Compute weighted total score from breakdown."""
        total = 0.0
        total += breakdown.name_suspicion * self.weights.get("name_suspicion", 0.0)
        total += breakdown.known_hallucination * self.weights.get("known_hallucination", 0.0)
        total += breakdown.content_risk * self.weights.get("content_risk", 0.0)
        total += breakdown.script_risk * self.weights.get("script_risk", 0.0)
        total += breakdown.newness * self.weights.get("newness", 0.0)
        total += breakdown.repo_missing * self.weights.get("repo_missing", 0.0)
        total += breakdown.maintainer_reputation * self.weights.get("maintainer_reputation", 0.0)
        total += breakdown.docs_absence * self.weights.get("docs_absence", 0.0)
        total += breakdown.provenance_risk * self.weights.get("provenance_risk", 0.0)
        total += breakdown.repo_asymmetry * self.weights.get("repo_asymmetry", 0.0)
        total += breakdown.download_anomaly * self.weights.get("download_anomaly", 0.0)
        total += breakdown.version_flip * self.weights.get("version_flip", 0.0)
        return min(1.0, max(0.0, total))

    def _score_name_suspicion(
        self, candidate: PackageCandidate
    ) -> tuple[float, list[str]]:
        """Score based on suspicious naming patterns."""
        score = 0.0
        reasons = []
        name = candidate.name.lower()

        # Check for suspicious prefixes
        for prefix in self.heuristics["suspicious_prefixes"]:
            if name.startswith(prefix):
                score = max(score, 0.8)
                reasons.append(f"Contains brand prefix '{prefix}'")

        # Check for suspicious suffixes
        for suffix in self.heuristics["suspicious_suffixes"]:
            if name.endswith(suffix):
                score = max(score, 0.6)
                reasons.append(f"Contains trope suffix '{suffix}'")

        # Check similarity to canonical packages
        ecosystem_key = "pypi" if candidate.ecosystem == Ecosystem.PYPI else "npm"
        canonical_list = self.heuristics["canonical_packages"].get(ecosystem_key, [])

        for canonical in canonical_list:
            similarity = fuzz.ratio(name, canonical.lower())
            distance = 100 - similarity

            # If very similar but not exact
            if 0 < distance <= self.heuristics["fuzzy_threshold"]:
                similarity_score = 1.0 - (distance / self.heuristics["fuzzy_threshold"])
                score = max(score, similarity_score * 0.9)
                reasons.append(
                    f"Very similar to '{canonical}' (distance: {distance})"
                )

        return min(1.0, score), reasons

    def _score_newness(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on package age."""
        reasons = []
        now = datetime.now(timezone.utc)

        # Ensure created_at is timezone-aware
        created_at = candidate.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        age_days = (now - created_at).days
        threshold = self.heuristics["new_package_days"]

        if age_days <= 0:
            score = 1.0
            reasons.append("Published today")
        elif age_days <= threshold:
            score = 1.0 - (age_days / threshold)
            reasons.append(f"Only {age_days} days old")
        else:
            score = 0.0

        return score, reasons

    def _score_repo_missing(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on missing repository/homepage."""
        reasons = []

        has_repo = bool(candidate.repository)
        has_homepage = bool(candidate.homepage)

        if not has_repo and not has_homepage:
            score = 1.0
            reasons.append("No repository or homepage")
        elif not has_repo:
            score = 0.5
            reasons.append("No repository URL")
        elif not has_homepage:
            score = 0.5
            reasons.append("No homepage URL")
        else:
            score = 0.0

        return score, reasons

    def _score_maintainer_reputation(
        self, candidate: PackageCandidate
    ) -> tuple[float, list[str]]:
        """Score based on maintainer count."""
        reasons = []
        count = candidate.maintainers_count

        if count <= 1:
            score = 1.0
            reasons.append("Single maintainer")
        elif count == 2:
            score = 0.5
            reasons.append("Only 2 maintainers")
        else:
            score = 0.0

        return score, reasons

    def _score_script_risk(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on install scripts (npm only)."""
        reasons = []

        if candidate.ecosystem == Ecosystem.NPM and candidate.has_install_scripts:
            score = 1.0
            reasons.append("Has install/preinstall/postinstall scripts")
        else:
            score = 0.0

        return score, reasons

    def _score_known_hallucination(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on known hallucination corpus."""
        corpus_file = self.heuristics.get("corpus", {}).get("hallucinations_file")
        is_hallu, reason = is_known_hallucination(candidate.name, corpus_file)
        
        if is_hallu:
            return 1.0, [reason]
        return 0.0, []

    def _score_content_risk(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on code-level risk (npm scripts OR PyPI artifacts)."""
        if is_offline_mode():
            return 0.0, ["Offline mode: content analysis skipped"]

        if candidate.ecosystem == Ecosystem.NPM:
            return self._score_npm_content_risk(candidate)
        elif candidate.ecosystem == Ecosystem.PYPI:
            return self._score_pypi_content_risk(candidate)
        
        return 0.0, []

    def _score_npm_content_risk(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score npm package script content."""
        # Get scripts from raw_metadata
        scripts = candidate.raw_metadata.get("latest_scripts", {})
        if not scripts:
            # Fallback: check versions
            versions = candidate.raw_metadata.get("versions", {})
            dist_tags = candidate.raw_metadata.get("dist-tags", {})
            latest = dist_tags.get("latest", candidate.version)
            if latest in versions:
                scripts = versions[latest].get("scripts", {})
        
        if not scripts:
            return 0.0, []
        
        risk, reasons = lint_scripts(scripts)
        return risk, reasons

    def _score_pypi_content_risk(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score PyPI artifact static analysis."""
        try:
            # Get download URLs
            urls = fetch_latest_release_files(candidate.raw_metadata)
            if not urls:
                return 0.0, ["No release files found"]

            # Separate sdist and wheel
            sdist_url = None
            wheel_url = None
            for url in urls:
                if url.endswith(".tar.gz") or url.endswith(".tgz"):
                    sdist_url = url
                elif url.endswith(".whl"):
                    wheel_url = wheel_url or url  # Take first wheel

            if not sdist_url and not wheel_url:
                return 0.0, []

            # Download and analyze (with timeout)
            timeout = self.policy.sources.get("pypi", {}).get("timeout", 10)
            sdist_dir = download_and_unpack(sdist_url, timeout) if sdist_url else None
            wheel_dir = download_and_unpack(wheel_url, timeout) if wheel_url else None

            reasons = []
            total_risk = 0.0

            # Compare sdist vs wheel
            if sdist_dir and wheel_dir:
                has_mismatch, mismatch_reasons = compare_sdist_wheel(sdist_dir, wheel_dir)
                if has_mismatch:
                    total_risk += 0.5
                    reasons.extend(mismatch_reasons)

            # Static scan (prefer sdist, fallback to wheel)
            scan_dir = sdist_dir or wheel_dir
            if scan_dir:
                static_risk, static_reasons = static_scan(scan_dir)
                total_risk += static_risk
                reasons.extend(static_reasons)

            # Cleanup
            cleanup_tempdir(sdist_dir)
            cleanup_tempdir(wheel_dir)

            return min(total_risk, 1.0), reasons

        except Exception as e:
            return 0.0, [f"Artifact analysis failed: {str(e)[:50]}"]

    def _score_docs_absence(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on missing documentation."""
        reasons = []
        
        has_homepage = bool(candidate.homepage)
        has_repo = bool(candidate.repository)
        
        # Check for documentation URL in project_urls (PyPI)
        if candidate.ecosystem == Ecosystem.PYPI:
            project_urls = candidate.raw_metadata.get("info", {}).get("project_urls") or {}
            has_docs = any(
                key in project_urls
                for key in ["Documentation", "Docs", "documentation", "docs"]
            )
        else:
            # For npm, documentation is typically in homepage or repo
            has_docs = False
        
        if not has_homepage and not has_repo and not has_docs:
            score = 1.0
            reasons.append("No homepage, repository, or documentation links")
        elif not has_docs:
            score = 0.5
            reasons.append("No dedicated documentation URL")
        else:
            score = 0.0
        
        return score, reasons

    def _score_provenance_risk(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on provenance indicators."""
        if is_offline_mode():
            return 0.0, ["Offline mode: provenance check skipped"]

        lookups = self.heuristics.get("lookups", {})
        if not lookups.get("enable_github", True):
            return 0.0, ["Provenance checks disabled"]

        if candidate.ecosystem == Ecosystem.NPM:
            packument = candidate.raw_metadata
            risk = npm_provenance_indicator(packument)
            if risk > 0.8:
                return risk, ["No npm provenance signatures found"]
            elif risk > 0.0:
                return risk, ["Weak provenance indicators"]
            return 0.0, []
        
        elif candidate.ecosystem == Ecosystem.PYPI:
            risk = pypi_provenance_indicator(candidate.raw_metadata)
            # Don't penalize PyPI packages yet (provenance not widely adopted)
            return 0.0, []
        
        return 0.0, []

    def _score_repo_asymmetry(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on package vs repository age mismatch."""
        if is_offline_mode():
            return 0.0, ["Offline mode: repo check skipped"]

        if not candidate.repository:
            return 0.0, []  # Handled by repo_missing

        lookups = self.heuristics.get("lookups", {})
        if not lookups.get("enable_github", True):
            return 0.0, ["GitHub checks disabled"]

        repo_age_days, _, _, _ = get_repo_facts(candidate.repository)
        if repo_age_days is None:
            return 0.0, []

        asymmetry = compute_repo_asymmetry(candidate.created_at, repo_age_days)
        
        if asymmetry > 0.5:
            return asymmetry, [
                f"Package age vs repo age mismatch (asymmetry: {asymmetry:.2f})"
            ]
        
        return asymmetry, []

    def _score_download_anomaly(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on download anomalies."""
        if is_offline_mode():
            return 0.0, ["Offline mode: download check skipped"]

        if candidate.ecosystem != Ecosystem.NPM:
            return 0.0, []  # Only npm for now

        lookups = self.heuristics.get("lookups", {})
        if not lookups.get("enable_npm_downloads", True):
            return 0.0, ["Download checks disabled"]

        downloads = npm_weekly_downloads(candidate.name)
        if downloads is None:
            return 0.0, []

        now = datetime.now(timezone.utc)
        created_at = candidate.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = (now - created_at).days

        anomaly = compute_download_anomaly(downloads, age_days)
        
        if anomaly > 0.3:
            return anomaly, [
                f"Unusual download pattern: {downloads} downloads/week for {age_days}-day-old package"
            ]
        
        return anomaly, []

    def _score_version_flip(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on version history flips."""
        if is_offline_mode():
            return 0.0, ["Offline mode: version history check skipped"]

        packument = candidate.raw_metadata
        risk, reasons = analyze_version_flip(
            candidate.ecosystem.value, candidate.name, packument
        )
        
        return risk, reasons
