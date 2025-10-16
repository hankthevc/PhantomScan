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
# Export feed to hunts CSV
make hunts

# Or manually:
python scripts/export_feed_to_hunts.py
```

This creates `hunts/radar_feed.csv` which you can use with:
- **Splunk**: `| inputlookup radar_feed.csv` (see `hunts/splunk/`)
- **KQL/Sentinel**: `externaldata()` with the CSV (see `hunts/kql/`)
- **Detection**: Cross-reference package names with your endpoint/container telemetry

## 🐳 Docker

```bash
# Build and run everything
docker-compose up

# Access Streamlit at http://localhost:8501
# Access API at http://localhost:8000/docs
```

## 🔌 API Usage

The FastAPI service provides programmatic access:

```bash
# Health check
curl http://localhost:8000/health

# Get latest feed
curl http://localhost:8000/feed/latest

# Get specific date feed
curl http://localhost:8000/feed/2024-10-16

# Score a package
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "ecosystem": "pypi",
    "name": "requests2",
    "version": "2.32.0",
    "repository": null,
    "has_install_scripts": false
  }'

# Interactive docs at http://localhost:8000/docs
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

## ☁️ Deploy to Streamlit Cloud (Optional)

For a public demo:

1. Fork this repo
2. Sign in to [Streamlit Cloud](https://share.streamlit.io)
3. Create a new app:
   - **Repository**: `your-fork/phantom-dependency-radar`
   - **Branch**: `main`
   - **Main file path**: `webapp/app.py`
   - **Python version**: `3.11`
4. The app will auto-deploy and update on commits

Note: Streamlit Cloud reads feeds from the repo's `data/feeds/` directory. The daily GitHub Actions workflow will automatically commit new feeds.

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.
