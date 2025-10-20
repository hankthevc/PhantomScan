"""Score package candidates for risk."""

from datetime import UTC, datetime

import pandas as pd
from rich.console import Console

from radar.registry.existence import exists_in_registry
from radar.scoring.heuristics import PackageScorer
from radar.storage import StorageManager
from radar.types import PackageCandidate, ScoredCandidate, WatchlistEntry
from radar.utils import get_data_path, load_jsonl, load_policy

console = Console()


def score_candidates(
    date_str: str | None = None,
) -> tuple[list[ScoredCandidate], list[WatchlistEntry]]:
    """Score candidates from raw data for a given date.

    Args:
        date_str: Date string (default: today)

    Returns:
        Tuple of (scored_candidates, watchlist_entries)
    """
    if date_str is None:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")

    policy = load_policy()
    scorer = PackageScorer(policy)
    strict_mode = policy.feed.get("strict", True)

    # Load raw candidates
    raw_path = get_data_path(date_str, "raw")
    all_candidates = []

    for ecosystem_file in raw_path.glob("*.jsonl"):
        data = load_jsonl(ecosystem_file)
        for item in data:
            try:
                candidate = PackageCandidate(**item)
                all_candidates.append(candidate)
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to parse candidate: {e}[/yellow]")

    if not all_candidates:
        console.print(f"[yellow]No candidates found for {date_str}[/yellow]")
        return [], []

    # Check existence and score
    scored = []
    watchlist: list[WatchlistEntry] = []

    console.print(f"[cyan]Checking {len(all_candidates)} candidates against registries...[/cyan]")

    for candidate in all_candidates:
        # Check if package exists in registry
        exists, reason = exists_in_registry(candidate.ecosystem.value, candidate.name, policy)

        if strict_mode and not exists:
            # In strict mode, skip scoring and add to watchlist
            watchlist.append(
                WatchlistEntry(
                    ecosystem=candidate.ecosystem,
                    name=candidate.name,
                    not_found_reason=reason,
                    first_seen_at=datetime.now(UTC),
                )
            )
            continue

        # Score the candidate
        breakdown = scorer.score(candidate)
        breakdown.exists_in_registry = exists
        breakdown.not_found_reason = reason if not exists else None

        if not exists:
            breakdown.reasons.append(f"Package not found in registry ({reason})")

        total_score = scorer.compute_weighted_score(breakdown)

        scored.append(
            ScoredCandidate(
                candidate=candidate,
                score=total_score,
                breakdown=breakdown,
                scored_at=datetime.now(UTC),
            )
        )

    # Sort by score descending
    scored.sort(key=lambda x: x.score, reverse=True)

    console.print(
        f"[green]✓ Scored {len(scored)} candidates, {len(watchlist)} in watchlist[/green]"
    )

    # Save to Parquet
    processed_path = get_data_path(date_str, "processed")
    parquet_file = processed_path / "scored.parquet"

    records = []
    for sc in scored:
        records.append(
            {
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
                "version_flip": sc.breakdown.version_flip,
                "readme_plagiarism": sc.breakdown.readme_plagiarism,
                "exists_in_registry": sc.breakdown.exists_in_registry,
                "not_found_reason": sc.breakdown.not_found_reason or "",
                "homepage": sc.candidate.homepage,
                "repository": sc.candidate.repository,
                "maintainers_count": sc.candidate.maintainers_count,
                "has_install_scripts": sc.candidate.has_install_scripts,
                "reasons": "; ".join(sc.breakdown.reasons),
            }
        )

    df = pd.DataFrame(records)
    df.to_parquet(parquet_file, index=False)
    console.print(f"[green]✓ Saved scored results to {parquet_file}[/green]")

    # Save to DuckDB
    with StorageManager() as storage:
        storage.insert_scored_candidates(scored, date_str)
        console.print(f"[green]✓ Inserted {len(scored)} candidates into DuckDB[/green]")

    console.print(f"[bold green]Scored {len(scored)} candidates[/bold green]")
    return scored, watchlist
