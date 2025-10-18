"""Fetch packages from data sources."""

from datetime import datetime
from typing import Union

from rich.console import Console
from rich.progress import track

from radar.sources.npm import NpmSource
from radar.sources.pypi import PyPISource
from radar.types import PackageCandidate
from radar.utils import get_data_path, save_jsonl

console = Console()


def fetch_packages(
    ecosystems: list[str], limit: int = 400, date_str: str | None = None
) -> list[PackageCandidate]:
    """Fetch packages from specified ecosystems.

    Args:
        ecosystems: List of ecosystem names (e.g., ["pypi", "npm"])
        limit: Maximum packages to fetch per ecosystem
        date_str: Date string for output path (default: today)

    Returns:
        Combined list of package candidates
    """
    if date_str is None:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    all_candidates = []
    sources: list[Union[PyPISource, NpmSource]] = []

    # Initialize sources
    if "pypi" in ecosystems:
        sources.append(PyPISource())
    if "npm" in ecosystems:
        sources.append(NpmSource())

    # Fetch from each source
    for source in track(sources, description="Fetching packages..."):
        try:
            candidates = source.fetch_recent(limit)
            all_candidates.extend(candidates)

            # Save raw data
            raw_path = get_data_path(date_str, "raw") / f"{source.ecosystem.value}.jsonl"
            raw_data = [c.model_dump(mode="json") for c in candidates]
            save_jsonl(raw_data, raw_path)

            console.print(
                f"[green]✓ Saved {len(candidates)} {source.ecosystem.value} packages to {raw_path}[/green]"
            )

        except Exception as e:
            console.print(f"[red]✗ Error fetching from {source.ecosystem.value}: {e}[/red]")

        finally:
            source.close()

    console.print(f"[bold green]Total fetched: {len(all_candidates)} packages[/bold green]")
    return all_candidates
