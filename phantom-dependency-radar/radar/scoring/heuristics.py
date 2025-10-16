"""Heuristics for scoring package suspiciousness."""

import re
from datetime import datetime, timedelta
from typing import List

from rapidfuzz import fuzz
from rich.console import Console

from ..types import Ecosystem, PackageCandidate, PolicyConfig, ScoreBreakdown
from ..utils import load_policy

console = Console()


class PackageScorer:
    """Package risk scorer using configurable heuristics."""
    
    def __init__(self, policy: PolicyConfig = None):
        self.policy = policy or load_policy()
        self.scoring_config = self.policy.scoring
        self.weights = self.scoring_config.weights
    
    def score_package(self, package: PackageCandidate) -> ScoreBreakdown:
        """
        Score a package candidate for suspiciousness.
        
        Args:
            package: The package to score
            
        Returns:
            ScoreBreakdown with detailed scoring information
        """
        reasons = []
        
        # Calculate individual scores
        name_suspicion, name_reasons = self._score_name_suspicion(package)
        reasons.extend(name_reasons)
        
        newness, newness_reasons = self._score_newness(package)
        reasons.extend(newness_reasons)
        
        repo_missing, repo_reasons = self._score_repo_missing(package)
        reasons.extend(repo_reasons)
        
        maintainer_reputation, maintainer_reasons = self._score_maintainer_reputation(package)
        reasons.extend(maintainer_reasons)
        
        script_risk, script_reasons = self._score_script_risk(package)
        reasons.extend(script_reasons)
        
        # Calculate weighted final score
        final_score = (
            name_suspicion * self.weights.name_suspicion +
            newness * self.weights.newness +
            repo_missing * self.weights.repo_missing +
            maintainer_reputation * self.weights.maintainer_reputation +
            script_risk * self.weights.script_risk
        )
        
        return ScoreBreakdown(
            package_name=package.name,
            ecosystem=package.ecosystem,
            name_suspicion=name_suspicion,
            newness=newness,
            repo_missing=repo_missing,
            maintainer_reputation=maintainer_reputation,
            script_risk=script_risk,
            final_score=final_score,
            reasons=reasons
        )
    
    def _score_name_suspicion(self, package: PackageCandidate) -> tuple[float, List[str]]:
        """Score name-based suspicion indicators."""
        score = 0.0
        reasons = []
        
        name = package.name.lower()
        
        # Check for suspicious prefixes
        for prefix in self.scoring_config.suspicious_prefixes:
            if name.startswith(prefix.lower()):
                score = max(score, 0.8)
                reasons.append(f"Uses suspicious brand prefix: {prefix}")
        
        # Check for suspicious suffixes
        for suffix in self.scoring_config.suspicious_suffixes:
            if name.endswith(suffix.lower()):
                score = max(score, 0.6)
                reasons.append(f"Uses suspicious suffix: {suffix}")
        
        # Check similarity to canonical packages
        ecosystem_key = package.ecosystem.value
        canonical_packages = self.scoring_config.canonical_packages.get(ecosystem_key, [])
        
        for canonical in canonical_packages:
            similarity = fuzz.ratio(name, canonical.lower()) / 100.0
            
            # High similarity but not exact match is suspicious
            if 0.70 <= similarity < 1.0:
                similarity_score = min(similarity * 1.2, 1.0)  # Boost similarity score
                if similarity_score > score:
                    score = similarity_score
                    reasons.append(f"Very similar to popular package '{canonical}' (similarity: {similarity:.2f})")
                break
        
        # Check for common typosquatting patterns
        typosquat_patterns = [
            r'.*\d+$',  # Ends with numbers (e.g., requests2)
            r'.*-?py$',  # Ends with -py or py
            r'.*-?js$',  # Ends with -js or js
            r'.*-?x$',   # Ends with -x or x
            r'.*[il1].*[il1].*',  # Multiple i/l/1 characters (visual similarity)
        ]
        
        for pattern in typosquat_patterns:
            if re.match(pattern, name):
                score = max(score, 0.4)
                reasons.append(f"Matches typosquatting pattern: {pattern}")
                break
        
        return min(score, 1.0), reasons
    
    def _score_newness(self, package: PackageCandidate) -> tuple[float, List[str]]:
        """Score package newness."""
        reasons = []
        
        if not package.created_at:
            return 0.0, reasons
        
        days_old = (datetime.utcnow() - package.created_at).days
        new_package_threshold = self.scoring_config.new_package_days
        
        if days_old <= new_package_threshold:
            # Linear scale: 1.0 for day 0, 0.0 for threshold day
            score = max(0.0, 1.0 - (days_old / new_package_threshold))
            
            if days_old == 0:
                reasons.append("Created today")
            elif days_old <= 7:
                reasons.append(f"Very new package (created {days_old} days ago)")
            else:
                reasons.append(f"New package (created {days_old} days ago)")
            
            return score, reasons
        
        return 0.0, reasons
    
    def _score_repo_missing(self, package: PackageCandidate) -> tuple[float, List[str]]:
        """Score missing repository/homepage information."""
        reasons = []
        
        has_repo = bool(package.repository_url and package.repository_url.strip())
        has_homepage = bool(package.homepage_url and package.homepage_url.strip())
        
        if not has_repo and not has_homepage:
            reasons.append("No repository or homepage URL provided")
            return 1.0, reasons
        elif not has_repo:
            reasons.append("No repository URL provided")
            return 0.5, reasons
        elif not has_homepage:
            # Less suspicious if repo is provided but homepage is missing
            return 0.2, reasons
        
        return 0.0, reasons
    
    def _score_maintainer_reputation(self, package: PackageCandidate) -> tuple[float, List[str]]:
        """Score maintainer reputation based on count."""
        reasons = []
        
        maintainer_count = package.maintainers_count or 1
        
        if maintainer_count <= 1:
            reasons.append("Single maintainer")
            return 1.0, reasons
        elif maintainer_count == 2:
            reasons.append("Only 2 maintainers")
            return 0.5, reasons
        else:
            # 3+ maintainers is generally good
            return 0.0, reasons
    
    def _score_script_risk(self, package: PackageCandidate) -> tuple[float, List[str]]:
        """Score npm install script risk."""
        reasons = []
        
        # Only applies to npm packages
        if package.ecosystem != Ecosystem.NPM:
            return 0.0, reasons
        
        if package.has_install_scripts:
            reasons.append("Has potentially dangerous install scripts (install/preinstall/postinstall)")
            return 1.0, reasons
        
        return 0.0, reasons
    
    def get_risk_level(self, score: float) -> str:
        """Convert numeric score to risk level."""
        if score >= 0.8:
            return "CRITICAL"
        elif score >= 0.6:
            return "HIGH"
        elif score >= 0.4:
            return "MEDIUM"
        elif score >= 0.2:
            return "LOW"
        else:
            return "MINIMAL"
    
    def get_risk_color(self, score: float) -> str:
        """Get color for risk level display."""
        if score >= 0.8:
            return "red"
        elif score >= 0.6:
            return "orange"
        elif score >= 0.4:
            return "yellow"
        elif score >= 0.2:
            return "blue"
        else:
            return "green"