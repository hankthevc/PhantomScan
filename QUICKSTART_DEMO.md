# PhantomScan - Quick Demo Guide

## 🚀 30-Second Demo

```bash
# 1. Setup (one time)
make setup

# 2. Run pipeline (offline mode for demo)
RADAR_OFFLINE=1 make run

# 3. Launch web app
make app
```

Visit **http://localhost:8501** to explore the UI!

---

## 📱 UI Walkthrough

### 1. Home Page
- Overview of PhantomScan capabilities
- Shows online/offline mode status
- Links to all features

### 2. Live Feed (📈)
- Browse suspicious packages by date
- Filter by ecosystem (PyPI/npm), score, name
- See risk factors and score breakdowns
- Export to CSV or Markdown

### 3. Candidate Explorer (🔎)
- Search specific packages
- View detailed scoring analysis
- Understand detection heuristics

### 4. Casefile Generator (📄)
- Create investigation reports
- Markdown format for documentation
- Includes all metadata and risk factors

### 5. Settings (⚙️)
- View/edit detection policy
- Adjust scoring weights
- Configure thresholds

---

## 🔌 API Demo

```bash
# Start API server
make api

# Test endpoints
curl http://localhost:8000/health

curl http://localhost:8000/feed/latest

curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "ecosystem": "pypi",
    "name": "requests2",
    "version": "2.32.0"
  }'
```

Interactive docs: **http://localhost:8000/docs**

---

## 🎯 Hunt Pack Demo

```bash
# Export feed to CSV
make hunts

# View the hunt data
cat hunts/radar_feed.csv

# Show sample Splunk query
cat hunts/splunk/slopsquat_hunts.spl

# Show sample KQL query
cat hunts/kql/slopsquat_hunts.kql
```

**Use Case:** Cross-reference suspicious packages with your endpoint/container telemetry to detect installations.

---

## 🐳 Docker Demo

```bash
# One command to run everything
docker-compose up

# Services:
# - Worker: Runs radar pipeline
# - Web: http://localhost:8501
# - API: http://localhost:8000
```

---

## 📊 Sample Demo Flow

### Scenario: Security Team Daily Review

1. **Morning Feed Check**
   ```bash
   RADAR_OFFLINE=1 make run  # In production: make run
   ```
   - Fetches latest packages from PyPI & npm
   - Scores using multi-factor heuristics
   - Generates top-50 threat intel feed

2. **Review in Web UI**
   - Open http://localhost:8501
   - Navigate to Live Feed
   - Filter for high-risk packages (score > 0.7)
   - Investigate suspicious patterns

3. **Generate Hunt Queries**
   ```bash
   make hunts
   ```
   - Export feed to CSV
   - Load into Splunk/Sentinel
   - Query endpoint logs for installations

4. **Deep Dive Investigation**
   - Select a suspicious package
   - Generate casefile report
   - Document findings
   - Share with team

5. **API Integration**
   - Integrate with CI/CD
   - Score packages before deployment
   - Block high-risk packages

---

## 🎬 Demo Script (5 minutes)

### Minute 1: Problem Statement
> "Supply chain attacks via slopsquatting are on the rise. Attackers publish packages with names like 'requests2', 'openai-tools', 'copilot-sdk' to trick developers. We need automated detection."

### Minute 2: Show the Pipeline
```bash
RADAR_OFFLINE=1 radar run-all
```
> "Our radar monitors PyPI and npm continuously, scoring packages by name suspicion, metadata, install scripts, and more."

### Minute 3: Show the UI
Open http://localhost:8501
> "Security teams can browse the daily feed, filter by risk, and see detailed score breakdowns for each package."

### Minute 4: Show Hunt Pack
```bash
make hunts
cat hunts/radar_feed.csv
```
> "We export the feed to SIEM-ready CSV. Teams can cross-reference with endpoint logs to detect installations in their environment."

### Minute 5: Show API
```bash
curl http://localhost:8000/feed/latest
```
> "The REST API enables CI/CD integration. Teams can block high-risk packages before deployment."

---

## 💡 Key Features to Highlight

1. ✅ **Multi-Ecosystem**: PyPI + npm (extensible to Rust, Go, Ruby)
2. ✅ **Offline Demo Mode**: Works without network for presentations
3. ✅ **Daily Automation**: GitHub Actions runs at 03:23 UTC
4. ✅ **Hunt Integration**: Export to Splunk, Sentinel, any SIEM
5. ✅ **Full Stack**: CLI + Web + API + Docker
6. ✅ **Open Source**: MIT license, defensive security only

---

## 🔒 Security & Ethics

**This tool is for DEFENSIVE SECURITY ONLY.**

- ✅ Detect supply chain attacks
- ✅ Protect your organization
- ✅ Share threat intel with community

- ❌ Never publish malicious packages
- ❌ Never probe systems without authorization
- ❌ Always verify findings manually before action

---

## 📚 Learn More

- Full README: [README.md](README.md)
- Deployment Guide: [DEPLOYMENT.md](DEPLOYMENT.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)
- Security Policy: [SECURITY.md](SECURITY.md)
- Demo Checklist: [DEMO_READY.md](DEMO_READY.md)

---

## 🆘 Troubleshooting

### "No feed data available"
```bash
RADAR_OFFLINE=1 make run
```

### "Module not found"
```bash
make setup
```

### "Port already in use"
```bash
# Change ports in docker-compose.yml or:
pkill -f streamlit
pkill -f uvicorn
```

### "API returns 404"
```bash
# Make sure feed exists
ls data/feeds/$(date +%Y-%m-%d)/
```

---

**Happy Hunting! 🔭**
