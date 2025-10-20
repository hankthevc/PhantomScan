"""Generate top-N threat intelligence feeds."""

import csv
from datetime import UTC, datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from radar.types import WatchlistEntry
from radar.utils import get_data_path, load_policy, save_json

console = Console()


def generate_feed(
    date_str: str | None = None,
    top_n: int | None = None,
    watchlist: list[WatchlistEntry] | None = None,
) -> None:
    """Generate top-N feed from scored candidates.

    Args:
        date_str: Date string (default: today)
        top_n: Number of top candidates (default: from policy)
        watchlist: Optional list of non-existent packages
    """
    if date_str is None:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")

    policy = load_policy()
    if top_n is None:
        top_n = policy.feed["top_n"]

    min_score = policy.feed.get("min_score", 0.0)
    write_watchlist = policy.feed.get("write_watchlist", True)

    # Load scored candidates from storage
    from radar.storage import StorageManager

    with StorageManager() as storage:
        df = storage.get_scored_candidates(date_str)

    if df.empty:
        console.print(f"[yellow]No scored candidates found for {date_str}[/yellow]")
        return

    # Filter by minimum score and take top N
    df = df[df["score"] >= min_score]
    df = df.head(top_n)

    # Convert to JSON-serializable format
    feed_data = []
    for _, row in df.iterrows():
        breakdown_dict = {
            "name_suspicion": float(row["name_suspicion"]),
            "newness": float(row["newness"]),
            "repo_missing": float(row["repo_missing"]),
            "maintainer_reputation": float(row["maintainer_reputation"]),
            "script_risk": float(row["script_risk"]),
        }

        # Add new fields if they exist in the dataframe
        if "version_flip" in row:
            breakdown_dict["version_flip"] = float(row["version_flip"])
        if "readme_plagiarism" in row:
            breakdown_dict["readme_plagiarism"] = float(row["readme_plagiarism"])
        if "exists_in_registry" in row:
            breakdown_dict["exists_in_registry"] = bool(row["exists_in_registry"])
        if "not_found_reason" in row and row["not_found_reason"]:
            breakdown_dict["not_found_reason"] = str(row["not_found_reason"])

        feed_data.append(
            {
                "ecosystem": row["ecosystem"],
                "name": row["name"],
                "version": row["version"],
                "created_at": row["created_at"].isoformat(),
                "score": float(row["score"]),
                "breakdown": breakdown_dict,
                "homepage": row["homepage"] if row["homepage"] else None,
                "repository": row["repository"] if row["repository"] else None,
                "maintainers_count": int(row["maintainers_count"]),
                "has_install_scripts": bool(row["has_install_scripts"]),
                "reasons": row["reasons"].split("; ") if row["reasons"] else [],
                "scored_at": row["scored_at"].isoformat(),
            }
        )

    # Save JSON feed
    feed_path = get_data_path(date_str, "feeds")
    json_file = feed_path / "topN.json"
    save_json(feed_data, json_file)
    console.print(f"[green]✓ Saved JSON feed to {json_file}[/green]")

    # Save CSV feed
    csv_file = feed_path / "topN.csv"
    _save_feed_csv(feed_data, csv_file)
    console.print(f"[green]✓ Saved CSV feed to {csv_file}[/green]")

    # Generate Markdown feed
    md_file = feed_path / "feed.md"
    _render_markdown_feed(feed_data, date_str, md_file)
    console.print(f"[green]✓ Saved Markdown feed to {md_file}[/green]")

    # Save watchlist if requested
    if write_watchlist and watchlist:
        _save_watchlist(watchlist, feed_path)

    console.print(f"[bold green]Generated feed with {len(feed_data)} candidates[/bold green]")


def _render_markdown_feed(feed_data: list[dict], date_str: str, output_path: Path) -> None:
    """Render Markdown feed using Jinja template."""
    template_dir = Path("radar/reports/templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("feed.md.j2")

    markdown = template.render(
        date=date_str,
        candidates=feed_data,
        total_count=len(feed_data),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown)


def _save_feed_csv(feed_data: list[dict], output_path: Path) -> None:
    """Save feed data to CSV format."""
    if not feed_data:
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="") as csvfile:
        # Flatten breakdown for CSV
        fieldnames = [
            "ecosystem",
            "name",
            "version",
            "created_at",
            "score",
            "name_suspicion",
            "newness",
            "repo_missing",
            "maintainer_reputation",
            "script_risk",
            "version_flip",
            "readme_plagiarism",
            "exists_in_registry",
            "not_found_reason",
            "homepage",
            "repository",
            "maintainers_count",
            "has_install_scripts",
            "reasons",
        ]

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()

        for item in feed_data:
            row = {
                "ecosystem": item["ecosystem"],
                "name": item["name"],
                "version": item["version"],
                "created_at": item["created_at"],
                "score": item["score"],
                "homepage": item.get("homepage") or "",
                "repository": item.get("repository") or "",
                "maintainers_count": item["maintainers_count"],
                "has_install_scripts": item["has_install_scripts"],
                "reasons": "; ".join(item.get("reasons", [])),
            }
            # Flatten breakdown
            breakdown = item.get("breakdown", {})
            row.update(
                {
                    "name_suspicion": breakdown.get("name_suspicion", 0),
                    "newness": breakdown.get("newness", 0),
                    "repo_missing": breakdown.get("repo_missing", 0),
                    "maintainer_reputation": breakdown.get("maintainer_reputation", 0),
                    "script_risk": breakdown.get("script_risk", 0),
                    "version_flip": breakdown.get("version_flip", 0),
                    "readme_plagiarism": breakdown.get("readme_plagiarism", 0),
                    "exists_in_registry": breakdown.get("exists_in_registry", True),
                    "not_found_reason": breakdown.get("not_found_reason", ""),
                }
            )
            writer.writerow(row)


def _save_watchlist(watchlist: list[WatchlistEntry], output_path: Path) -> None:
    """Save watchlist to JSON and CSV formats."""
    if not watchlist:
        return

    # Convert to dict format
    watchlist_data = [
        {
            "ecosystem": entry.ecosystem.value,
            "name": entry.name,
            "not_found_reason": entry.not_found_reason,
            "first_seen_at": entry.first_seen_at.isoformat(),
        }
        for entry in watchlist
    ]

    # Save JSON
    json_file = output_path / "watchlist.json"
    save_json(watchlist_data, json_file)
    console.print(f"[cyan]✓ Saved watchlist JSON to {json_file}[/cyan]")

    # Save CSV
    csv_file = output_path / "watchlist.csv"
    with csv_file.open("w", newline="") as csvfile:
        fieldnames = ["ecosystem", "name", "not_found_reason", "first_seen_at"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(watchlist_data)

    console.print(f"[cyan]✓ Saved watchlist CSV to {csv_file} ({len(watchlist)} entries)[/cyan]")
