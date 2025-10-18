"""Command-line interface for PhantomScan."""

from datetime import datetime, timezone
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
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
    import os
    
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    offline_mode = os.getenv("RADAR_OFFLINE", "0") == "1"
    
    if offline_mode:
        console.print("[yellow]🔌 OFFLINE MODE - Using seed data[/yellow]")

    console.print(f"[bold cyan]🚀 Running full radar pipeline for {date}...[/bold cyan]\n")

    try:
        # Step 1: Fetch
        console.print("[bold blue]Step 1/3: Fetching packages...[/bold blue]")
        candidates = fetch_packages(ecosystems, limit, date)
        console.print(f"[green]✓ Fetched {len(candidates)} packages[/green]\n")

        if not candidates:
            console.print("[yellow]⚠️ No candidates fetched.[/yellow]")
            
            # If online mode failed, suggest offline mode
            if not offline_mode:
                console.print("[yellow]💡 Tip: Try running with RADAR_OFFLINE=1 for demo mode[/yellow]")
                raise typer.Exit(code=1)
            else:
                console.print("[yellow]⚠️ No seed data available. Exiting gracefully.[/yellow]")
                raise typer.Exit(code=0)

        # Step 2: Score
        console.print("[bold blue]Step 2/3: Scoring candidates...[/bold blue]")
        scored = score_candidates(date)
        console.print(f"[green]✓ Scored {len(scored)} candidates[/green]\n")

        if not scored:
            console.print("[yellow]⚠️ No candidates scored. Exiting gracefully.[/yellow]")
            raise typer.Exit(code=0)

        # Step 3: Feed
        console.print("[bold blue]Step 3/3: Generating feed...[/bold blue]")
        generate_feed(date, top)
        console.print(f"[green]✓ Generated feed[/green]\n")

        source_label = "OFFLINE SEED" if offline_mode else "LIVE DATA"
        console.print(f"[bold green]✅ Pipeline complete! Feed saved to data/feeds/{date}/[/bold green]")
        console.print(f"[bold green]📊 Source: {source_label}[/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Pipeline interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    
    except Exception as e:
        console.print(f"\n[red]❌ Pipeline failed: {e}[/red]")
        
        # If not in offline mode, suggest it
        if not offline_mode:
            console.print("[yellow]💡 Tip: Try running with RADAR_OFFLINE=1 for offline demo mode[/yellow]")
        
        raise typer.Exit(code=1)


@app.command()
def analyze(
    ecosystem: Annotated[str, typer.Option("--ecosystem", "-e", help="Package ecosystem (pypi or npm)")],
    name: Annotated[str, typer.Option("--name", "-n", help="Package name")],
    show_alternatives: Annotated[bool, typer.Option("--alternatives", "-a", help="Show safer alternatives")] = True,
) -> None:
    """Analyze a specific package and show risk assessment."""
    from radar.scoring.heuristics import PackageScorer
    from radar.sources.npm import NpmSource
    from radar.sources.pypi import PyPISource
    from radar.suggestions.alternatives import suggest_alternatives
    from radar.types import Ecosystem
    from radar.utils import load_policy

    console.print(f"[bold cyan]🔍 Analyzing {ecosystem}/{name}...[/bold cyan]\n")

    try:
        # Parse ecosystem
        if ecosystem.lower() == "pypi":
            eco = Ecosystem.PYPI
            source = PyPISource()
        elif ecosystem.lower() == "npm":
            eco = Ecosystem.NPM
            source = NpmSource()
        else:
            console.print(f"[red]❌ Invalid ecosystem: {ecosystem}[/red]")
            console.print("[yellow]💡 Valid ecosystems: pypi, npm[/yellow]")
            raise typer.Exit(code=1)

        # Fetch package metadata
        console.print(f"[blue]📦 Fetching metadata for {name}...[/blue]")
        
        # For now, we need to fetch from the source
        # This is a simplified version - in production, we'd have a dedicated fetch method
        if ecosystem.lower() == "pypi":
            candidate = source._fetch_package_metadata(name)
        elif ecosystem.lower() == "npm":
            # For npm, we'd need to fetch the packument
            import httpx
            policy = load_policy()
            url = f"https://registry.npmjs.org/{name}"
            client = httpx.Client(timeout=10, follow_redirects=True)
            response = client.get(url)
            if response.status_code == 404:
                console.print(f"[red]❌ Package not found: {name}[/red]")
                raise typer.Exit(code=1)
            response.raise_for_status()
            doc = response.json()
            candidate = source._parse_npm_doc(doc)
            client.close()

        if not candidate:
            console.print(f"[red]❌ Failed to fetch package: {name}[/red]")
            raise typer.Exit(code=1)

        console.print(f"[green]✓ Fetched metadata[/green]\n")

        # Score the package
        console.print("[blue]🧮 Computing risk score...[/blue]")
        policy = load_policy()
        scorer = PackageScorer(policy)
        breakdown = scorer.score(candidate)
        total_score = scorer.compute_weighted_score(breakdown)
        console.print(f"[green]✓ Computed score[/green]\n")

        # Display results
        console.print("=" * 60)
        console.print(f"[bold]Package:[/bold] {candidate.name}")
        console.print(f"[bold]Ecosystem:[/bold] {candidate.ecosystem.value}")
        console.print(f"[bold]Version:[/bold] {candidate.version}")
        console.print(f"[bold]Created:[/bold] {candidate.created_at.strftime('%Y-%m-%d')}")
        console.print(f"[bold]Homepage:[/bold] {candidate.homepage or '❌ Not provided'}")
        console.print(f"[bold]Repository:[/bold] {candidate.repository or '❌ Not provided'}")
        console.print("=" * 60)

        # Risk score with color coding
        if total_score >= 0.7:
            color = "red"
            risk_level = "HIGH RISK"
        elif total_score >= 0.4:
            color = "yellow"
            risk_level = "MEDIUM RISK"
        else:
            color = "green"
            risk_level = "LOW RISK"

        console.print(f"\n[bold {color}]🎯 RISK SCORE: {total_score:.2f} / 1.00 ({risk_level})[/bold {color}]\n")

        # Score breakdown
        console.print("[bold]📊 Score Breakdown:[/bold]")
        console.print(f"  • Name Suspicion:        {breakdown.name_suspicion:.2f}")
        console.print(f"  • Known Hallucination:   {breakdown.known_hallucination:.2f}")
        console.print(f"  • Content Risk:          {breakdown.content_risk:.2f}")
        console.print(f"  • Script Risk:           {breakdown.script_risk:.2f}")
        console.print(f"  • Newness:               {breakdown.newness:.2f}")
        console.print(f"  • Repository Missing:    {breakdown.repo_missing:.2f}")
        console.print(f"  • Maintainer Reputation: {breakdown.maintainer_reputation:.2f}")
        console.print(f"  • Docs Absence:          {breakdown.docs_absence:.2f}")
        console.print(f"  • Provenance Risk:       {breakdown.provenance_risk:.2f}")
        console.print(f"  • Repo Asymmetry:        {breakdown.repo_asymmetry:.2f}")
        console.print(f"  • Download Anomaly:      {breakdown.download_anomaly:.2f}")
        console.print(f"  • Version Flip:          {breakdown.version_flip:.2f}")

        # Risk factors
        if breakdown.reasons:
            console.print(f"\n[bold]⚠️  Risk Factors ({len(breakdown.reasons)}):[/bold]")
            for reason in breakdown.reasons:
                console.print(f"  • {reason}")

        # Safer alternatives
        if show_alternatives:
            console.print("\n[bold]💡 Safer Alternatives:[/bold]")
            canonical_list = policy.heuristics.get("canonical_packages", {}).get(
                candidate.ecosystem.value, []
            )
            alternatives = suggest_alternatives(candidate.name, candidate.ecosystem, canonical_list)
            
            if alternatives:
                for alt_name, similarity in alternatives:
                    console.print(f"  • {alt_name} (similarity: {similarity:.0f}%)")
            else:
                console.print("  [dim]No close alternatives found[/dim]")

        console.print("\n" + "=" * 60)
        source.close()

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Analysis interrupted by user[/yellow]")
        raise typer.Exit(code=130)
    
    except Exception as e:
        console.print(f"\n[red]❌ Analysis failed: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def version() -> None:
    """Show version information."""
    from radar import __version__

    console.print(f"PhantomScan version [bold cyan]{__version__}[/bold cyan]")


if __name__ == "__main__":
    app()
