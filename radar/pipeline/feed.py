"""Generate top-N threat intelligence feeds."""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from rich.console import Console

from radar.types import ScoredCandidate
from radar.utils import get_data_path, load_policy, save_json

console = Console()


def generate_feed(date_str: str | None = None, top_n: int | None = None) -> None:
    """Generate top-N feed from scored candidates.

    Args:
        date_str: Date string (default: today)
        top_n: Number of top candidates (default: from policy)
    """
    if date_str is None:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    policy = load_policy()
    if top_n is None:
        top_n = policy.feed["top_n"]

    min_score = policy.feed.get("min_score", 0.0)

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
        feed_data.append(
            {
                "ecosystem": row["ecosystem"],
                "name": row["name"],
                "version": row["version"],
                "created_at": row["created_at"].isoformat(),
                "score": float(row["score"]),
                "breakdown": {
                    "name_suspicion": float(row["name_suspicion"]),
                    "newness": float(row["newness"]),
                    "repo_missing": float(row["repo_missing"]),
                    "maintainer_reputation": float(row["maintainer_reputation"]),
                    "script_risk": float(row["script_risk"]),
                },
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

    # Generate Markdown feed
    md_file = feed_path / "feed.md"
    _render_markdown_feed(feed_data, date_str, md_file)
    console.print(f"[green]✓ Saved Markdown feed to {md_file}[/green]")

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
