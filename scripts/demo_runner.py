#!/usr/bin/env python3
"""
PhantomScan Demo Runner
Runs canned demo casefiles against the local FastAPI endpoint and prints scorecards.
"""

import argparse
import json
import os
import sys
import time
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DIMENSION_HINT_ORDER = [
    "name_suspicion",
    "newness",
    "repo_missing",
    "maintainer_reputation",
    "script_risk",
    "version_flip",
    "readme_plagiarism",
]


def post_json(url: str, payload: dict, timeout: float = 10.0) -> Any:
    """Post JSON to URL and return response."""
    req = Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except HTTPError as e:
        return {"_error": f"HTTP {e.code}: {e.reason}", "_payload": payload}
    except URLError as e:
        return {"_error": f"Network error: {e.reason}", "_payload": payload}
    except Exception as e:
        return {"_error": f"Unexpected error: {e}", "_payload": payload}


def _first_present(d: dict, keys: list[str]) -> Any:
    """Return first present key value from dict."""
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def extract_scores(resp: dict) -> tuple[Any, dict, list]:
    """Extract total score and dimension scores from API response."""
    if not isinstance(resp, dict):
        return None, {}, {}

    total = _first_present(resp, ["score", "total", "risk", "risk_score", "overall"])
    breakdown = _first_present(resp, ["breakdown", "dimensions", "component_scores", "scores"])
    reasons = resp.get("reasons", [])

    dim_scores = {}
    if isinstance(breakdown, dict):
        for k, v in breakdown.items():
            if isinstance(v, int | float):
                dim_scores[k] = float(v)
            elif isinstance(v, dict):
                val = _first_present(v, ["score", "risk", "value"])
                if isinstance(val, int | float):
                    dim_scores[k] = float(val)

    return total, dim_scores, reasons


def fmt_row(cols: list, widths: list[int]) -> str:
    """Format a row with given column widths."""
    return " | ".join(str(c).ljust(w) for c, w in zip(cols, widths, strict=False))


def print_scorecard(title: str, eco: str, results: list) -> None:
    """Print a formatted scorecard table."""
    if not results:
        print(f"\n=== {title} [{eco}] ===")
        print("No results to display")
        return

    name_w = max(12, *(len(r["name"]) for r in results))
    dims = DIMENSION_HINT_ORDER[:]

    # Collect all dimensions from results
    for r in results:
        _, ds, _ = r["extracted"]
        for k in ds:
            if k not in dims:
                dims.append(k)

    widths = [name_w, 7] + [max(6, len(d.replace("_", " ")[:6])) for d in dims]

    print(f"\n=== {title} [{eco}] ===")
    header_dims = [d.replace("_", " ").title()[:6] for d in dims]
    print(fmt_row(["Package", "Total", *header_dims], widths))
    print("-" * (sum(widths) + 3 * (len(widths) - 1)))

    for r in results:
        total, ds, _ = r["extracted"]
        if "_error" in r["raw"]:
            print(f"{r['name'].ljust(name_w)} | ERROR: {r['raw']['_error']}")
            continue

        tstr = f"{total:.2f}" if isinstance(total, int | float) else "—"
        row = [r["name"], tstr] + [f"{ds.get(d, 0):.2f}" if d in ds else "—" for d in dims]
        print(fmt_row(row, widths))


def main() -> int:
    """Main entry point."""
    ap = argparse.ArgumentParser(description="Run PhantomScan demo casefiles")
    ap.add_argument("casefile", help="Path to casefile JSON")
    ap.add_argument("--api-base", default="http://127.0.0.1:8000", help="API base URL")
    ap.add_argument("--endpoint", default="/score", help="Scoring endpoint")
    ap.add_argument("--timeout", type=float, default=10.0, help="Request timeout")
    ap.add_argument("--outdir", default="dist/demo", help="Output directory")
    args = ap.parse_args()

    # Load casefile
    try:
        with open(args.casefile) as f:
            case = json.load(f)
    except FileNotFoundError:
        print(f"Error: Casefile not found: {args.casefile}")
        return 1
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in casefile: {e}")
        return 1

    eco = case.get("ecosystem", "pypi")
    names = case.get("names", [])
    title = case.get("title", os.path.basename(args.casefile).replace(".json", ""))

    if not names:
        print("Error: No package names in casefile")
        return 1

    # Create output directory
    os.makedirs(args.outdir, exist_ok=True)
    tsdir = os.path.join(args.outdir, datetime.now(UTC).strftime("%Y%m%d-%H%M%S"))
    os.makedirs(tsdir, exist_ok=True)

    # Score each package
    results = []
    print(f"\n🔍 Scoring {len(names)} {eco} packages...")

    for n in names:
        payload = {"ecosystem": eco, "name": n, "maintainers_count": 1}
        url = args.api_base.rstrip("/") + args.endpoint

        print(f"  → {n}...", end="", flush=True)
        r = post_json(url, payload, timeout=args.timeout)

        if "_error" in r:
            print(f" ❌ {r['_error']}")
        else:
            total, _, _ = extract_scores(r)
            if isinstance(total, int | float):
                print(f" ✓ Score: {total:.2f}")
            else:
                print(" ✓")

        extracted = extract_scores(r)
        results.append({"name": n, "raw": r, "extracted": extracted})
        time.sleep(case.get("sleep_between_seconds", 0))

    # Print scorecard
    print_scorecard(title, eco, results)

    # Save results
    outfile = os.path.join(tsdir, f"{title}.json")
    with open(outfile, "w") as jf:
        json.dump(results, jf, indent=2)

    print(f"\n💾 Results saved to: {outfile}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
