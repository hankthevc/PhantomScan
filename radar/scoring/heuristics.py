"""Heuristic-based scoring for package candidates."""

from datetime import UTC, datetime

from rapidfuzz import fuzz

from radar.types import Ecosystem, PackageCandidate, PolicyConfig, ScoreBreakdown


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

        # 2. Newness
        newness_score, newness_reasons = self._score_newness(candidate)
        reasons.extend(newness_reasons)

        # 3. Repository missing
        repo_score, repo_reasons = self._score_repo_missing(candidate)
        reasons.extend(repo_reasons)

        # 4. Maintainer reputation
        maint_score, maint_reasons = self._score_maintainer_reputation(candidate)
        reasons.extend(maint_reasons)

        # 5. Script risk (npm only)
        script_score, script_reasons = self._score_script_risk(candidate)
        reasons.extend(script_reasons)

        # 6. Version flip (PyPI only) - requires enrichment
        version_flip_score = 0.0

        # 7. README plagiarism - requires enrichment
        readme_plagiarism_score = 0.0

        return ScoreBreakdown(
            name_suspicion=name_score,
            newness=newness_score,
            repo_missing=repo_score,
            maintainer_reputation=maint_score,
            script_risk=script_score,
            version_flip=version_flip_score,
            readme_plagiarism=readme_plagiarism_score,
            reasons=reasons,
        )

    def compute_weighted_score(self, breakdown: ScoreBreakdown) -> float:
        """Compute weighted total score from breakdown."""
        total = 0.0
        total += breakdown.name_suspicion * self.weights.get("name_suspicion", 0.30)
        total += breakdown.newness * self.weights.get("newness", 0.25)
        total += breakdown.repo_missing * self.weights.get("repo_missing", 0.15)
        total += breakdown.maintainer_reputation * self.weights.get("maintainer_reputation", 0.15)
        total += breakdown.script_risk * self.weights.get("script_risk", 0.10)
        total += breakdown.version_flip * self.weights.get("version_flip", 0.03)
        total += breakdown.readme_plagiarism * self.weights.get("readme_plagiarism", 0.02)
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
        now = datetime.now(UTC)

        # Ensure created_at is timezone-aware
        created_at = candidate.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

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
        """Score based on maintainer count and quality signals."""
        reasons = []
        count = candidate.maintainers_count
        score = 0.0

        # Base scoring on count
        if count <= 1:
            score = 1.0
            reasons.append("Single maintainer")
        elif count == 2:
            score = 0.5
            reasons.append("Only 2 maintainers")
        else:
            score = 0.0

        # Enhanced signals
        # Check for disposable email (major red flag)
        if candidate.disposable_email and count <= 1:
            score = 1.0
            reasons.append("Disposable email address detected")

        # Check for young maintainer account
        age_threshold = self.heuristics.get("thresholds", {}).get("maintainer_age_days", 14)
        if candidate.maintainers_age_hint_days is not None:
            if candidate.maintainers_age_hint_days < age_threshold:
                score = min(1.0, score + 0.3)
                reasons.append(f"Very young account ({candidate.maintainers_age_hint_days} days)")

        return min(1.0, score), reasons

    def _score_script_risk(self, candidate: PackageCandidate) -> tuple[float, list[str]]:
        """Score based on install scripts (npm only)."""
        reasons = []

        if candidate.ecosystem == Ecosystem.NPM and candidate.has_install_scripts:
            score = 1.0
            reasons.append("Has install/preinstall/postinstall scripts")
        else:
            score = 0.0

        return score, reasons
