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

### Smoke test the pipeline locally

```bash
# Offline demo-friendly run (creates data/feeds/TODAY/topN.json and feed.md)
RADAR_OFFLINE=1 make run
git add -A && git commit -m "chore: add first feed artifacts" && git push

# Try live pull (fallback to offline for demos if rate-limited)
make run
```

## 📊 Features

- **Live Feed**: Browse top-N suspicious packages by date with detailed risk scoring
- **Candidate Explorer**: Search and investigate individual packages with score breakdowns
- **Casefile Generator**: Create investigation reports in Markdown format
- **Hunt Pack**: Pre-built queries for KQL (Azure Sentinel) and Splunk to detect installations
- **Offline Mode**: Demo with seed data when network is unavailable
- **Daily Automation**: GitHub Actions workflow to run daily and commit feed artifacts

## 🏗️ Architecture

- **Data Sources**: PyPI RSS + JSON API, npm changes feed (no authentication required)
- **Scoring Engine**: Multi-factor heuristics (name suspicion, newness, repo presence, maintainer count, install scripts)
- **Storage**: Local files (JSONL/Parquet) + DuckDB for historical analysis
- **UI**: Streamlit for interactive exploration
- **API**: FastAPI for programmatic access
- **Automation**: GitHub Actions for daily scheduling

## 🔍 Using the Hunt Pack

Export today's feed to CSV and load into your SIEM:

```bash
# Export today's feed to CSV (demo helper)
python -c "import pandas as pd, json, os, datetime as dt; \
d=dt.date.today().isoformat(); p=f'data/feeds/{d}/topN.json'; \
pd.read_json(p).rename(columns={'name':'package_name'}).to_csv('hunts/radar_feed.csv', index=False)"

# Then run the hunts in hunts/splunk/ or hunts/kql/
```

Splunk users: `| inputlookup radar_feed.csv` is used in `hunts/splunk/slopsquat_hunts.spl`.
KQL users: see `externaldata()` examples in `hunts/kql/slopsquat_hunts.kql`.

## 🐳 Docker

```bash
# Build and run everything
docker-compose up

# Access Streamlit at http://localhost:8501
# Access API at http://localhost:8000
```

The compose stack includes:
- a small worker that runs `radar run-all`
- the Streamlit web app
- the FastAPI service

The `./data` directory is mounted so the app sees new feeds.

### Streamlit Community Cloud (optional)

- Set Python version to 3.11
- App entry point: `webapp/app.py`
- The app reads latest feed from `data/feeds` (kept small; Top-50 recommended). For public demos, you can also serve feeds from the repository raw path.

### API usage (curl)

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/feed/$(date +%Y-%m-%d)  # falls back to latest if missing
curl -s http://localhost:8000/score -H 'Content-Type: application/json' -d '{
  "ecosystem": "pypi",
  "name": "requests",
  "version": "2.31.0"
}'
```

### Screenshots

Two example screenshots to aid reviewers/recruiters:
- Live Feed table
- Casefile preview

(Add images under `webapp/assets/` and reference here.)

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
├── webapp/          # Streamlit UI
├── api/             # FastAPI service
├── hunts/           # SIEM queries (KQL + Splunk)
├── data/            # Raw pulls, scored results, feeds
├── config/          # Policy configuration
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

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.
