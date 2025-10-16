# PhantomScan Deployment Guide

This guide walks you through deploying PhantomScan in various environments.

## 📋 Prerequisites

- **Python 3.11+**
- **pip** and **virtualenv**
- **Git**
- **Docker** (optional, for containerized deployment)
- **GitHub repository access** (for CI/CD automation)

## 🚀 Quick Start (Local Development)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/your-org/phantom-dependency-radar.git
cd phantom-dependency-radar

# Install dependencies and pre-commit hooks
make setup
```

### 2. Run the Pipeline (Offline Demo)

```bash
# Run with sample data
export RADAR_OFFLINE=1
make run

# Or run with live data
make run
```

### 3. Launch the Web Interface

```bash
# Terminal 1: Launch Streamlit app
make app
# Visit http://localhost:8501

# Terminal 2: Launch FastAPI service
make api
# Visit http://localhost:8000/docs
```

## 🐳 Docker Deployment

### Build and Run with Docker Compose

```bash
# Build images
docker-compose build

# Run in offline mode (demo)
RADAR_OFFLINE=1 docker-compose up

# Run with live data
docker-compose up
```

### Individual Containers

```bash
# Build worker
docker build -f Dockerfile.worker -t phantom-worker .

# Build web app
docker build -f Dockerfile.app -t phantom-web .

# Build API
docker build -f Dockerfile.api -t phantom-api .

# Run worker once
docker run --rm -v $(pwd)/data:/app/data phantom-worker

# Run web app
docker run -d -p 8501:8501 -v $(pwd)/data:/app/data phantom-web

# Run API
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data phantom-api
```

## ☁️ Cloud Deployment

### AWS (EC2 + ECS)

1. **EC2 Instance**:
   ```bash
   # SSH into instance
   ssh ec2-user@your-instance

   # Install Docker
   sudo yum update -y
   sudo yum install docker -y
   sudo systemctl start docker

   # Clone and run
   git clone https://github.com/your-org/phantom-dependency-radar.git
   cd phantom-dependency-radar
   docker-compose up -d
   ```

2. **ECS (Fargate)**:
   - Push images to ECR
   - Create ECS task definitions for worker, web, and API
   - Schedule worker task with CloudWatch Events (daily)
   - Deploy web and API as services with ALB

### Google Cloud (Cloud Run)

```bash
# Build and push images
gcloud builds submit --tag gcr.io/PROJECT_ID/phantom-web -f Dockerfile.app .
gcloud builds submit --tag gcr.io/PROJECT_ID/phantom-api -f Dockerfile.api .

# Deploy web app
gcloud run deploy phantom-web \
  --image gcr.io/PROJECT_ID/phantom-web \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Deploy API
gcloud run deploy phantom-api \
  --image gcr.io/PROJECT_ID/phantom-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated

# Schedule worker with Cloud Scheduler
gcloud scheduler jobs create http radar-daily \
  --schedule "23 3 * * *" \
  --uri "https://WORKER_URL/run" \
  --http-method POST
```

### Azure (Container Instances)

```bash
# Create resource group
az group create --name phantom-rg --location eastus

# Create container registry
az acr create --resource-group phantom-rg --name phantomacr --sku Basic

# Build and push
az acr build --registry phantomacr --image phantom-web:latest -f Dockerfile.app .
az acr build --registry phantomacr --image phantom-api:latest -f Dockerfile.api .

# Deploy containers
az container create \
  --resource-group phantom-rg \
  --name phantom-web \
  --image phantomacr.azurecr.io/phantom-web:latest \
  --ports 8501 \
  --dns-name-label phantom-web

az container create \
  --resource-group phantom-rg \
  --name phantom-api \
  --image phantomacr.azurecr.io/phantom-api:latest \
  --ports 8000 \
  --dns-name-label phantom-api
```

## 🤖 GitHub Actions Automation

The included `.github/workflows/radar_daily.yml` runs the radar pipeline daily.

### Setup

1. **Enable Actions** in your repository settings

2. **Configure Secrets** (if needed):
   - Go to Settings > Secrets and variables > Actions
   - Add `RADAR_OFFLINE` (optional, set to `1` for demo mode)

3. **Customize Schedule**:
   Edit `.github/workflows/radar_daily.yml`:
   ```yaml
   schedule:
     - cron: '23 3 * * *'  # 03:23 UTC daily
   ```

4. **Manual Trigger**:
   ```bash
   # Via GitHub CLI
   gh workflow run radar_daily.yml

   # Via web UI
   # Actions > PhantomScan Daily Radar > Run workflow
   ```

## 🔧 Configuration

### Environment Variables

- `RADAR_OFFLINE` - Set to `1` to use seed data instead of live APIs
- `PYTHONPATH` - Add to path if running outside virtualenv

### Policy Configuration

Edit `config/policy.yml` to customize:
- Scoring weights
- Suspicious prefixes/suffixes
- Feed generation settings
- Network timeouts

## 📊 Monitoring

### Health Checks

- **Streamlit**: `http://localhost:8501/_stcore/health`
- **FastAPI**: `http://localhost:8000/health`

### Logs

```bash
# Docker logs
docker-compose logs -f web
docker-compose logs -f api

# Local logs
# Logs are written to stdout by default
```

### Metrics

Monitor:
- Pipeline run duration
- Number of candidates fetched
- Feed generation success rate
- API response times

## 🔒 Security Considerations

1. **API Rate Limiting**: Ensure respectful API usage (default: 10s timeout, 3 retries)

2. **Data Privacy**: Feed data may contain package names; avoid public exposure without review

3. **Network Access**: Whitelist PyPI and npm domains in firewall

4. **Credentials**: Never commit API keys or tokens (none required for PyPI/npm public APIs)

5. **Container Security**: Use non-root users in production Dockerfiles

## 🧪 Testing Deployment

### Smoke Tests

```bash
# Test CLI
radar --help
radar version

# Test pipeline (offline)
RADAR_OFFLINE=1 radar run-all

# Test API
curl http://localhost:8000/health

# Test Streamlit
curl http://localhost:8501/_stcore/health
```

### Integration Tests

```bash
# Run full test suite
make test

# Check code quality
make lint
make type
```

## 🔄 Updates and Maintenance

### Updating PhantomScan

```bash
# Pull latest changes
git pull origin main

# Reinstall dependencies
make setup

# Restart services
docker-compose down
docker-compose up -d --build
```

### Backup and Restore

```bash
# Backup data
tar -czf phantom-backup-$(date +%Y%m%d).tar.gz data/

# Restore
tar -xzf phantom-backup-20241016.tar.gz
```

## 🆘 Troubleshooting

### Common Issues

1. **"No module named 'radar'"**
   - Solution: Run `pip install -e .` or `make setup`

2. **"Feed not found"**
   - Solution: Run `radar run-all` to generate feeds

3. **"Connection timeout"**
   - Solution: Check network connectivity or set `RADAR_OFFLINE=1`

4. **"Permission denied" in Docker**
   - Solution: Add user to docker group: `sudo usermod -aG docker $USER`

### Debug Mode

```bash
# Enable verbose logging
python -m radar.cli run-all --help

# Check DuckDB
python -c "import duckdb; conn = duckdb.connect('data/radar.duckdb'); print(conn.execute('SHOW TABLES').fetchall())"
```

## 📞 Support

- **Issues**: https://github.com/your-org/phantom-dependency-radar/issues
- **Documentation**: See README.md
- **Security**: See SECURITY.md

## 📄 License

MIT License - see LICENSE file for details.
