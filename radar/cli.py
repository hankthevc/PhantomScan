"""Command-line interface for PhantomScan."""

from datetime import datetime
from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from radar.pipeline.fetch import fetch_packages
from radar.pipeline.feed import generate_feed
from radar.pipeline.score import score_candidates

app = typer.Typer(
    name="radar",
    help="PhantomScan - Phantom Dependency Radar for slopsquatting detection",
    add_completion=False,
)
console = Console()


@app.command()
def fetch(
    ecosystems: Annotated[
        list[str],
        typer.Option("--ecosystems", "-e", help="Ecosystems to fetch (pypi, npm)"),
    ] = ["pypi", "npm"],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max packages per ecosystem")] = 400,
    date: Annotated[
        Optional[str], typer.Option("--date", "-d", help="Date string (YYYY-MM-DD)")
    ] = None,
) -> None:
    """Fetch recent packages from registries."""
    console.print("[bold blue]🔭 Fetching packages...[/bold blue]")

    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    candidates = fetch_packages(ecosystems, limit, date)
    console.print(f"[bold green]✓ Fetched {len(candidates)} packages for {date}[/bold green]")


@app.command()
def score(
    date: Annotated[
        Optional[str], typer.Option("--date", "-d", help="Date string (YYYY-MM-DD)")
    ] = None,
) -> None:
    """Score fetched candidates."""
    console.print("[bold blue]🧮 Scoring candidates...[/bold blue]")

    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    scored = score_candidates(date)
    console.print(f"[bold green]✓ Scored {len(scored)} candidates for {date}[/bold green]")


@app.command()
def feed(
    date: Annotated[
        Optional[str], typer.Option("--date", "-d", help="Date string (YYYY-MM-DD)")
    ] = None,
    top: Annotated[Optional[int], typer.Option("--top", "-n", help="Top N candidates")] = None,
) -> None:
    """Generate top-N threat intelligence feed."""
    console.print("[bold blue]📊 Generating feed...[/bold blue]")

    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    generate_feed(date, top)
    console.print(f"[bold green]✓ Generated feed for {date}[/bold green]")


@app.command(name="run-all")
def run_all(
    ecosystems: Annotated[
        list[str],
        typer.Option("--ecosystems", "-e", help="Ecosystems to fetch (pypi, npm)"),
    ] = ["pypi", "npm"],
    limit: Annotated[int, typer.Option("--limit", "-l", help="Max packages per ecosystem")] = 400,
    top: Annotated[Optional[int], typer.Option("--top", "-n", help="Top N candidates")] = None,
) -> None:
    """Run complete pipeline: fetch → score → feed."""
    date = datetime.utcnow().strftime("%Y-%m-%d")

    console.print(f"[bold cyan]🚀 Running full radar pipeline for {date}...[/bold cyan]\n")

    # Step 1: Fetch
    console.print("[bold blue]Step 1/3: Fetching packages...[/bold blue]")
    candidates = fetch_packages(ecosystems, limit, date)
    console.print(f"[green]✓ Fetched {len(candidates)} packages[/green]\n")

    if not candidates:
        console.print("[yellow]No candidates fetched. Exiting.[/yellow]")
        return

    # Step 2: Score
    console.print("[bold blue]Step 2/3: Scoring candidates...[/bold blue]")
    scored = score_candidates(date)
    console.print(f"[green]✓ Scored {len(scored)} candidates[/green]\n")

    # Step 3: Feed
    console.print("[bold blue]Step 3/3: Generating feed...[/bold blue]")
    generate_feed(date, top)
    console.print(f"[green]✓ Generated feed[/green]\n")

    console.print(f"[bold green]✅ Pipeline complete! Feed saved to data/feeds/{date}/[/bold green]")


@app.command()
def version() -> None:
    """Show version information."""
    from radar import __version__

    console.print(f"PhantomScan version [bold cyan]{__version__}[/bold cyan]")


if __name__ == "__main__":
    app()
