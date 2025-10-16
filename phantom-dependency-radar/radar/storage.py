"""Storage utilities for the Phantom Dependency Radar."""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
from rich.console import Console

from .types import PackageCandidate, ScoredCandidate
from .utils import get_date_str, load_json, save_json

console = Console()


class RadarStorage:
    """Storage manager for radar data using DuckDB and files."""
    
    def __init__(self, db_path: Path = Path("data/radar.duckdb")):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize DuckDB database with required tables."""
        with duckdb.connect(str(self.db_path)) as conn:
            # Create packages table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS packages (
                    date DATE,
                    ecosystem VARCHAR,
                    name VARCHAR,
                    version VARCHAR,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    description VARCHAR,
                    author VARCHAR,
                    maintainers_count INTEGER,
                    repository_url VARCHAR,
                    homepage_url VARCHAR,
                    has_install_scripts BOOLEAN,
                    raw_data JSON,
                    PRIMARY KEY (date, ecosystem, name)
                )
            """)
            
            # Create scores table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    date DATE,
                    ecosystem VARCHAR,
                    name VARCHAR,
                    name_suspicion DOUBLE,
                    newness DOUBLE,
                    repo_missing DOUBLE,
                    maintainer_reputation DOUBLE,
                    script_risk DOUBLE,
                    final_score DOUBLE,
                    reasons JSON,
                    scored_at TIMESTAMP,
                    PRIMARY KEY (date, ecosystem, name)
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_packages_date ON packages(date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_packages_score ON scores(date, final_score DESC)")
    
    def store_packages(self, packages: List[PackageCandidate], date: Optional[str] = None) -> None:
        """Store package candidates for a given date."""
        if date is None:
            date = get_date_str()
        
        if not packages:
            console.print(f"[yellow]No packages to store for {date}[/yellow]")
            return
        
        # Convert to DataFrame
        records = []
        for pkg in packages:
            record = {
                'date': date,
                'ecosystem': pkg.ecosystem.value,
                'name': pkg.name,
                'version': pkg.version,
                'created_at': pkg.created_at,
                'updated_at': pkg.updated_at,
                'description': pkg.description,
                'author': pkg.author,
                'maintainers_count': pkg.maintainers_count,
                'repository_url': pkg.repository_url,
                'homepage_url': pkg.homepage_url,
                'has_install_scripts': pkg.has_install_scripts,
                'raw_data': pkg.raw_data
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        with duckdb.connect(str(self.db_path)) as conn:
            # Insert or replace packages for this date
            conn.execute(f"DELETE FROM packages WHERE date = '{date}'")
            conn.register('packages_df', df)
            conn.execute("INSERT INTO packages SELECT * FROM packages_df")
            
        console.print(f"[green]Stored {len(packages)} packages for {date}[/green]")
    
    def store_scores(self, scored_candidates: List[ScoredCandidate], date: Optional[str] = None) -> None:
        """Store scored candidates for a given date."""
        if date is None:
            date = get_date_str()
        
        if not scored_candidates:
            console.print(f"[yellow]No scores to store for {date}[/yellow]")
            return
        
        # Convert to DataFrame
        records = []
        for scored in scored_candidates:
            record = {
                'date': date,
                'ecosystem': scored.candidate.ecosystem.value,
                'name': scored.candidate.name,
                'name_suspicion': scored.score.name_suspicion,
                'newness': scored.score.newness,
                'repo_missing': scored.score.repo_missing,
                'maintainer_reputation': scored.score.maintainer_reputation,
                'script_risk': scored.score.script_risk,
                'final_score': scored.score.final_score,
                'reasons': scored.score.reasons,
                'scored_at': scored.score.scored_at
            }
            records.append(record)
        
        df = pd.DataFrame(records)
        
        with duckdb.connect(str(self.db_path)) as conn:
            # Insert or replace scores for this date
            conn.execute(f"DELETE FROM scores WHERE date = '{date}'")
            conn.register('scores_df', df)
            conn.execute("INSERT INTO scores SELECT * FROM scores_df")
            
        console.print(f"[green]Stored {len(scored_candidates)} scores for {date}[/green]")
    
    def get_packages(self, date: str, ecosystem: Optional[str] = None) -> List[PackageCandidate]:
        """Retrieve packages for a given date."""
        with duckdb.connect(str(self.db_path)) as conn:
            query = "SELECT * FROM packages WHERE date = ?"
            params = [date]
            
            if ecosystem:
                query += " AND ecosystem = ?"
                params.append(ecosystem)
            
            df = conn.execute(query, params).df()
        
        packages = []
        for _, row in df.iterrows():
            pkg = PackageCandidate(
                name=row['name'],
                ecosystem=row['ecosystem'],
                version=row['version'],
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                description=row['description'],
                author=row['author'],
                maintainers_count=row['maintainers_count'],
                repository_url=row['repository_url'],
                homepage_url=row['homepage_url'],
                has_install_scripts=row['has_install_scripts'],
                raw_data=row['raw_data'] or {}
            )
            packages.append(pkg)
        
        return packages
    
    def get_top_scored_packages(self, date: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get top scored packages for a date."""
        with duckdb.connect(str(self.db_path)) as conn:
            query = """
                SELECT 
                    s.*,
                    p.version,
                    p.created_at,
                    p.repository_url,
                    p.homepage_url,
                    p.maintainers_count
                FROM scores s
                JOIN packages p ON s.date = p.date 
                    AND s.ecosystem = p.ecosystem 
                    AND s.name = p.name
                WHERE s.date = ?
                ORDER BY s.final_score DESC
                LIMIT ?
            """
            
            df = conn.execute(query, [date, limit]).df()
        
        return df.to_dict('records')
    
    def search_packages(self, name_pattern: str, date: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Search packages by name pattern."""
        with duckdb.connect(str(self.db_path)) as conn:
            query = """
                SELECT 
                    p.*,
                    s.final_score,
                    s.reasons
                FROM packages p
                LEFT JOIN scores s ON p.date = s.date 
                    AND p.ecosystem = s.ecosystem 
                    AND p.name = s.name
                WHERE p.name ILIKE ?
            """
            params = [f"%{name_pattern}%"]
            
            if date:
                query += " AND p.date = ?"
                params.append(date)
            
            query += " ORDER BY COALESCE(s.final_score, 0) DESC LIMIT ?"
            params.append(limit)
            
            df = conn.execute(query, params).df()
        
        return df.to_dict('records')
    
    def cleanup_old_data(self, keep_days: int = 30) -> None:
        """Clean up old data beyond keep_days."""
        cutoff_date = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
        
        with duckdb.connect(str(self.db_path)) as conn:
            # Clean up database tables
            deleted_packages = conn.execute(
                "DELETE FROM packages WHERE date < ?", 
                [cutoff_date]
            ).fetchone()[0]
            
            deleted_scores = conn.execute(
                "DELETE FROM scores WHERE date < ?", 
                [cutoff_date]
            ).fetchone()[0]
        
        # Clean up raw files
        raw_dir = Path("data/raw")
        if raw_dir.exists():
            for date_dir in raw_dir.iterdir():
                if date_dir.is_dir() and date_dir.name < cutoff_date:
                    shutil.rmtree(date_dir)
                    console.print(f"[yellow]Removed old raw data: {date_dir}[/yellow]")
        
        # Clean up processed files
        processed_dir = Path("data/processed")
        if processed_dir.exists():
            for date_dir in processed_dir.iterdir():
                if date_dir.is_dir() and date_dir.name < cutoff_date:
                    shutil.rmtree(date_dir)
                    console.print(f"[yellow]Removed old processed data: {date_dir}[/yellow]")
        
        if deleted_packages > 0 or deleted_scores > 0:
            console.print(f"[yellow]Cleaned up {deleted_packages} packages and {deleted_scores} scores older than {keep_days} days[/yellow]")


def get_storage() -> RadarStorage:
    """Get a RadarStorage instance."""
    return RadarStorage()


# File-based storage utilities for feeds and reports

def save_daily_feed(feed_data: Dict[str, Any], date: str) -> Path:
    """Save daily feed data as JSON."""
    feed_dir = Path(f"data/feeds/{date}")
    feed_dir.mkdir(parents=True, exist_ok=True)
    
    feed_path = feed_dir / "topN.json"
    save_json(feed_data, feed_path, pretty=True)
    
    console.print(f"[green]Saved daily feed to {feed_path}[/green]")
    return feed_path


def load_daily_feed(date: str) -> Optional[Dict[str, Any]]:
    """Load daily feed data from JSON."""
    feed_path = Path(f"data/feeds/{date}/topN.json")
    return load_json(feed_path)


def save_casefile(content: str, ecosystem: str, package_name: str, date: str) -> Path:
    """Save a casefile as Markdown."""
    feed_dir = Path(f"data/feeds/{date}")
    feed_dir.mkdir(parents=True, exist_ok=True)
    
    safe_name = package_name.replace("/", "_").replace("@", "_at_")
    casefile_path = feed_dir / f"case_{ecosystem}_{safe_name}.md"
    
    with open(casefile_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    console.print(f"[green]Saved casefile to {casefile_path}[/green]")
    return casefile_path


def get_available_feed_dates() -> List[str]:
    """Get list of available feed dates."""
    feeds_dir = Path("data/feeds")
    if not feeds_dir.exists():
        return []
    
    dates = []
    for date_dir in feeds_dir.iterdir():
        if date_dir.is_dir() and (date_dir / "topN.json").exists():
            dates.append(date_dir.name)
    
    return sorted(dates, reverse=True)  # Most recent first