"""Fetch packages from data sources."""

from datetime import datetime, timezone

from rich.console import Console
from rich.progress import track

from radar.sources.npm import NpmSource
from radar.sources.pypi import PyPISource
from radar.types import Ecosystem, PackageCandidate
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
    import os
    
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    all_candidates = []
    sources = []
    offline_mode = os.getenv("RADAR_OFFLINE", "0") == "1"

    # Initialize sources
    if "pypi" in ecosystems:
        sources.append(PyPISource())
    if "npm" in ecosystems:
        sources.append(NpmSource())

    # Fetch from each source with graceful error handling
    for source in track(sources, description="Fetching packages..."):
        ecosystem_name = source.ecosystem.value
        
        try:
            candidates = source.fetch_recent(limit)
            
            if not candidates:
                console.print(f"[yellow]⚠️ No candidates from {ecosystem_name}[/yellow]")
                continue
            
            all_candidates.extend(candidates)

            # Save raw data
            raw_path = get_data_path(date_str, "raw") / f"{ecosystem_name}.jsonl"
            raw_data = [c.model_dump(mode="json") for c in candidates]
            save_jsonl(raw_data, raw_path)

            mode_label = "(offline)" if offline_mode else "(online)"
            console.print(
                f"[green]✓ Saved {len(candidates)} {ecosystem_name} packages {mode_label} to {raw_path}[/green]"
            )

        except Exception as e:
            console.print(f"[red]✗ Error fetching from {ecosystem_name}: {e}[/red]")
            
            # If online mode failed, suggest offline mode
            if not offline_mode:
                console.print(f"[yellow]💡 Tip: Set RADAR_OFFLINE=1 to use seed data for {ecosystem_name}[/yellow]")

        finally:
            try:
                source.close()
            except Exception:
                pass  # Ignore cleanup errors

    if all_candidates:
        console.print(f"[bold green]Total fetched: {len(all_candidates)} packages[/bold green]")
    else:
        console.print("[yellow]⚠️ No packages fetched from any source[/yellow]")
        
    return all_candidates
