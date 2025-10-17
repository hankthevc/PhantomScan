#!/usr/bin/env python3
"""Export today's feed to CSV for hunt packs (Splunk/KQL)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def main() -> None:
    """Export feed to hunts CSV."""
    # Get today's date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # Look for today's feed, or use the latest available
    feed_path = Path(f"data/feeds/{today}/topN.json")
    
    if not feed_path.exists():
        # Find latest feed
        feeds_dir = Path("data/feeds")
        if not feeds_dir.exists():
            print(f"❌ No feeds directory found at {feeds_dir}")
            sys.exit(1)
        
        dates = sorted(
            [d.name for d in feeds_dir.iterdir() if d.is_dir() and (d / "topN.json").exists()],
            reverse=True
        )
        
        if not dates:
            print("❌ No feeds found")
            sys.exit(1)
        
        latest_date = dates[0]
        feed_path = feeds_dir / latest_date / "topN.json"
        print(f"ℹ️  Using latest feed: {latest_date}")
    
    # Load and convert to CSV
    try:
        df = pd.read_json(feed_path)
        
        # Rename columns for SIEM compatibility
        df = df.rename(columns={
            "name": "package_name",
            "created_at": "publish_date",
        })
        
        # Select key columns for hunts
        hunt_columns = [
            "package_name",
            "ecosystem", 
            "version",
            "publish_date",
            "score",
            "repository",
            "has_install_scripts"
        ]
        
        df_export = df[hunt_columns]
        
        # Save to hunts directory
        output_path = Path("hunts/radar_feed.csv")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_export.to_csv(output_path, index=False)
        
        print(f"✅ Exported {len(df_export)} packages to {output_path}")
        print(f"📊 Ecosystems: PyPI={sum(df['ecosystem']=='pypi')}, npm={sum(df['ecosystem']=='npm')}")
        print(f"⚠️  High-risk (>0.7): {sum(df['score']>0.7)}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
