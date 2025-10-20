# PhantomScan

A real-time slopsquatting monitor for PyPI and npm packages, designed to detect suspicious package publications that may be supply-chain attacks.

## 🎯 What is Slopsquatting?

Slopsquatting is a supply-chain attack where adversaries publish packages with names similar to popular libraries (e.g., `requests2`, `openai-tools`, `langchain-sdk`) to trick developers into installing malicious code. This tool continuously monitors package registries, scores candidates by risk, and generates actionable threat intelligence.

## 🚀 Quick Start

```bash
# Install dependencies
make setup

# Run the daily radar job (fetch, score, feed)
make run

# Launch the Streamlit web app
make app

# Launch the FastAPI service
make api
```

## ▶ Quick Demo for Recruiters

PhantomScan ships with a **one-click demo** that showcases its 7-signal supply-chain risk engine against real PyPI and npm packages.

### Run Locally

```bash
# Terminal 1: Start the API backend
make demo-api

# Terminal 2: Run the PyPI demo
make demo

# Or run the npm demo
make demo-npm

# Optional: Launch the Streamlit UI
make demo-ui
```

Each run prints a compact scorecard showing the total risk score and breakdown across all 7 dimensions:

```
=== pypi_basics [pypi] ===
Package      | Total | Name   | Newnes | Repo   | Mainta | Script | Versio | Readme
-----------------------------------------------------------------------------
requests     | 0.15  | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00
urllib3      | 0.12  | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00
numpy        | 0.08  | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00
pandas       | 0.10  | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00   | 0.00
```

**Output files** are saved under `dist/demo/<timestamp>/` for easy sharing with stakeholders.

### What Gets Scored

PhantomScan analyzes 7 risk dimensions:
1. **Name Suspicion** - Brand prefixes, typos, fuzzy matching against popular packages
2. **Newness** - Recent package creation (higher risk for <30 days old)
3. **Repository Missing** - No source/documentation links
4. **Maintainer Reputation** - Single maintainer, disposable emails, young accounts
5. **Script Risk** - Presence of install/preinstall scripts (npm) or setup.py code execution
6. **Version Flip** - Sudden dependency increases or metadata changes (30-day window)
7. **README Plagiarism** - Content similarity detection (n-gram analysis)

## 📊 Features

- **Live Feed**: Browse top-N suspicious packages by date with detailed risk scoring
- **Candidate Explorer**: Search and investigate individual packages with score breakdowns
- **Quick Score Panel**: Real-time package scoring via API with interactive breakdown display
- **Casefile Generator**: Create investigation reports in Markdown format
- **Hunt Pack**: Pre-built queries for KQL (Azure Sentinel) and Splunk to detect installations
- **Offline Mode**: Demo with seed data when network is unavailable
- **Daily Automation**: GitHub Actions workflow to run daily and commit feed artifacts

### 🔬 Advanced Enrichment Features

- **Version Flip Analysis** (PyPI): Compare current vs most recent previous release within a rolling time window (default 30 days) to detect suspicious changes (dependency spikes of ≥8 packages, new documentation URLs, console scripts)
- **Maintainer Reputation**: Enhanced scoring with disposable email detection and account age signals
- **Dependents Enrichment** (Optional): Query libraries.io to adjust risk based on package adoption
- **README Plagiarism** (Coming Soon): Detect content similarity between package and repository READMEs

## 🛡️ Strict Mode & Watchlist

PhantomScan includes a **registry existence gate** to filter out packages that don't actually exist in their registries, reducing false positives from parsing errors or data inconsistencies.

### Configuration

Edit `config/policy.yml`:

```yaml
feed:
  strict: true              # Only real packages in main feed
  write_watchlist: true     # Emit watchlist files for non-existent packages

network:
  registry_timeout_seconds: 4  # Timeout for existence checks
```

### Behavior

| Mode | Main Feed | Watchlist | API `/score` |
|------|-----------|-----------|--------------|
| `strict=true` | Only packages verified in registry | All non-existent names | 404 for non-existent |
| `strict=false` | All packages (with `exists` flag) | Optional | 200 with `exists=false` |

### Files Generated

When `write_watchlist: true`, the pipeline creates:

```
data/feeds/YYYY-MM-DD/
  ├── topN.json           # Main feed (real packages only in strict mode)
  ├── topN.csv            # Main feed as CSV
  ├── watchlist.json      # Non-existent packages
  └── watchlist.csv       # Watchlist as CSV
```

### API Usage

```bash
# Score with strict mode (rejects non-existent packages)
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "ecosystem": "npm",
    "name": "fake-package-xyz",
    "strict_exists": true
  }'
# Returns 404: "Package not found in registry (reason: 404)"

# Score without strict mode (scores anyway)
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "ecosystem": "npm",
    "name": "fake-package-xyz",
    "strict_exists": false
  }'
# Returns 200 with breakdown.exists_in_registry = false

# Get watchlist for a date
curl http://localhost:8000/watchlist/2025-10-20

# Get latest watchlist
curl http://localhost:8000/watchlist/latest
```

### UI Integration

The Streamlit **Live Feed** page now includes two tabs:

- **✅ Active Packages**: Scored packages that exist in registries
- **⚠️ Watchlist**: Packages detected but not found in registry (with reasons: `404`, `timeout`, `offline`, `error`)

The **Quick Score** panel includes a "Strict Mode" toggle to control existence checking behavior.

### Offline Mode

When `RADAR_OFFLINE=1` is set, existence checks return `(False, "offline")` and packages are routed to the watchlist unless strict mode is disabled.

## 🏗️ Architecture

- **Data Sources**: PyPI RSS + JSON API, npm changes feed (no authentication required)
- **Scoring Engine**: Multi-factor heuristics with 7 dimensions:
  - Name suspicion (brand prefixes, typos, fuzzy matching)
  - Newness (package age)
  - Repository presence
  - Maintainer reputation (count, disposable emails, account age)
  - Script risk (install scripts)
  - Version flip (PyPI metadata changes)
  - README plagiarism (content similarity)
- **Enrichment**: Optional external API calls (libraries.io for dependents, GitHub for READMEs)
- **Storage**: Local files (JSONL/Parquet) + DuckDB for historical analysis
- **UI**: Streamlit for interactive exploration
- **API**: FastAPI with timeout protection and graceful degradation
- **Automation**: GitHub Actions for daily scheduling

## 🔍 Using the Hunt Pack

Export today's feed to CSV and load into your SIEM:

```bash
# For Splunk
python -c "import pandas as pd; pd.read_json('data/feeds/$(date +%Y-%m-%d)/topN.json').to_csv('radar_feed.csv', index=False)"

# Then run the hunts in hunts/splunk/ or hunts/kql/
```

## 🐳 Docker

```bash
# Build and run everything
docker-compose up

# Access Streamlit at http://localhost:8501
# Access API at http://localhost:8000
```

## 🧪 Testing

```bash
make test    # Run pytest with coverage
make lint    # Check code quality with ruff
make type    # Type check with mypy
```

## 🔒 Security & Ethics

This tool is designed for **defensive security research only**. See [SECURITY.md](SECURITY.md) for responsible use guidelines. Never publish malicious packages or probe systems without authorization.

## 📁 Repository Structure

```
phantom-dependency-radar/
├── radar/           # Core pipeline (sources, scoring, storage)
│   ├── analysis/    # Content analysis (README similarity)
│   ├── enrich/      # External enrichment (version flip, dependents)
│   ├── pipeline/    # ETL orchestration
│   ├── scoring/     # Multi-heuristic risk scoring
│   └── sources/     # PyPI and npm data sources
├── webapp/          # Streamlit UI with Quick Score panel
├── api/             # FastAPI service with timeout protection
├── hunts/           # SIEM queries (KQL + Splunk)
├── data/            # Raw pulls, scored results, feeds
├── config/          # Policy configuration (weights, thresholds)
└── tests/           # Unit and integration tests
```

## 📅 Daily Workflow

The GitHub Actions workflow (`.github/workflows/radar_daily.yml`) runs at 03:23 UTC daily:
1. Fetches latest packages from PyPI and npm
2. Scores each candidate using configured heuristics
3. Generates top-50 feed (JSON + Markdown)
4. Commits artifacts to `data/feeds/YYYY-MM-DD/`

## 🎨 Offline Mode

For demos or network-constrained environments:

```bash
export RADAR_OFFLINE=1
make run  # Uses seed data from data/samples/
```

## 🔑 Environment Variables

Optional environment variables for enhanced features:

- `RADAR_OFFLINE=1` - Enable offline mode (uses seed data)
- `GH_TOKEN=<token>` - GitHub Personal Access Token for README fetching (enrichment)
- `LIBRARIES_IO_KEY=<key>` - Libraries.io API key for dependents enrichment

To enable dependents enrichment, set `LIBRARIES_IO_KEY` and update `config/policy.yml`:

```yaml
heuristics:
  lookups:
    enable_dependents: true
```

## 🌐 API Usage

### Score a Package

```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "ecosystem": "pypi",
    "name": "requests2",
    "version": "2.0.0",
    "maintainers_count": 1
  }'
```

Response includes:
- Overall risk score (0.0 to 1.0)
- Breakdown by scoring dimension
- List of risk indicators

**Note**: The `/score` endpoint has a configurable timeout (default 8 seconds) to prevent long-running enrichment fan-outs. If enrichment services are overloaded, you may receive a `503 Temporary overload: scoring timed out` response. This can be tuned via `network.api_timeout_seconds` in `config/policy.yml`.

### Get Latest Feed

```bash
curl http://localhost:8000/feed/latest
```

### Health Check

```bash
curl http://localhost:8000/health
```

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.
