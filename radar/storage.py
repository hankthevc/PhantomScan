"""Storage management with DuckDB and file I/O."""

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from radar.types import ScoredCandidate
from radar.utils import ensure_dir, load_policy


class StorageManager:
    """Manage persistent storage with DuckDB."""

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize storage manager."""
        if db_path is None:
            policy = load_policy()
            db_path = policy.storage["duckdb_path"]

        self.db_path = Path(db_path)
        ensure_dir(self.db_path.parent)
        self.conn = duckdb.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS scored_candidates (
                date DATE,
                ecosystem VARCHAR,
                name VARCHAR,
                version VARCHAR,
                created_at TIMESTAMP,
                score DOUBLE,
                name_suspicion DOUBLE,
                newness DOUBLE,
                repo_missing DOUBLE,
                maintainer_reputation DOUBLE,
                script_risk DOUBLE,
                known_hallucination DOUBLE DEFAULT 0.0,
                content_risk DOUBLE DEFAULT 0.0,
                docs_absence DOUBLE DEFAULT 0.0,
                provenance_risk DOUBLE DEFAULT 0.0,
                repo_asymmetry DOUBLE DEFAULT 0.0,
                download_anomaly DOUBLE DEFAULT 0.0,
                version_flip DOUBLE DEFAULT 0.0,
                homepage VARCHAR,
                repository VARCHAR,
                maintainers_count INTEGER,
                has_install_scripts BOOLEAN,
                reasons JSON,
                scored_at TIMESTAMP,
                PRIMARY KEY (date, ecosystem, name)
            )
        """)

    def insert_scored_candidates(self, candidates: list[ScoredCandidate], date_str: str) -> None:
        """Insert scored candidates for a given date."""
        if not candidates:
            return

        records = []
        for sc in candidates:
            records.append(
                {
                    "date": date_str,
                    "ecosystem": sc.candidate.ecosystem.value,
                    "name": sc.candidate.name,
                    "version": sc.candidate.version,
                    "created_at": sc.candidate.created_at,
                    "score": sc.score,
                    "name_suspicion": sc.breakdown.name_suspicion,
                    "newness": sc.breakdown.newness,
                    "repo_missing": sc.breakdown.repo_missing,
                    "maintainer_reputation": sc.breakdown.maintainer_reputation,
                    "script_risk": sc.breakdown.script_risk,
                    "known_hallucination": sc.breakdown.known_hallucination,
                    "content_risk": sc.breakdown.content_risk,
                    "docs_absence": sc.breakdown.docs_absence,
                    "provenance_risk": sc.breakdown.provenance_risk,
                    "repo_asymmetry": sc.breakdown.repo_asymmetry,
                    "download_anomaly": sc.breakdown.download_anomaly,
                    "version_flip": sc.breakdown.version_flip,
                    "homepage": sc.candidate.homepage,
                    "repository": sc.candidate.repository,
                    "maintainers_count": sc.candidate.maintainers_count,
                    "has_install_scripts": sc.candidate.has_install_scripts,
                    "reasons": sc.breakdown.reasons,
                    "scored_at": sc.scored_at,
                }
            )

        df = pd.DataFrame(records)
        self.conn.execute("DELETE FROM scored_candidates WHERE date = ?", [date_str])
        self.conn.execute("INSERT INTO scored_candidates SELECT * FROM df")

    def get_scored_candidates(self, date_str: str) -> pd.DataFrame:
        """Retrieve scored candidates for a given date."""
        return self.conn.execute(
            "SELECT * FROM scored_candidates WHERE date = ? ORDER BY score DESC", [date_str]
        ).df()

    def get_all_dates(self) -> list[str]:
        """Get list of all dates with scored candidates."""
        result = self.conn.execute(
            "SELECT DISTINCT date FROM scored_candidates ORDER BY date DESC"
        ).fetchall()
        return [row[0] for row in result]

    def cleanup_old_data(self, retention_days: int) -> None:
        """Remove data older than retention period."""
        if retention_days <= 0:
            return

        self.conn.execute(
            "DELETE FROM scored_candidates WHERE date < CURRENT_DATE - INTERVAL ? DAY",
            [retention_days],
        )

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self) -> "StorageManager":
        """Context manager entry."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()
