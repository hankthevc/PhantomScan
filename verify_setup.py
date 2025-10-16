#!/usr/bin/env python3
"""Quick setup verification script for PhantomScan."""

import sys
from pathlib import Path


def check_file(path: str, description: str) -> bool:
    """Check if a file exists."""
    if Path(path).exists():
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} - MISSING")
        return False


def check_dir(path: str, description: str) -> bool:
    """Check if a directory exists."""
    if Path(path).is_dir():
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} - MISSING")
        return False


def main() -> int:
    """Run verification checks."""
    print("🔭 PhantomScan Setup Verification\n")

    checks = []

    # Core modules
    print("📦 Core Modules:")
    checks.append(check_file("radar/__init__.py", "Radar module"))
    checks.append(check_file("radar/cli.py", "CLI entrypoint"))
    checks.append(check_file("radar/types.py", "Type definitions"))
    checks.append(check_file("radar/utils.py", "Utility functions"))
    checks.append(check_file("radar/storage.py", "Storage manager"))

    # Data sources
    print("\n📡 Data Sources:")
    checks.append(check_file("radar/sources/base.py", "Base source class"))
    checks.append(check_file("radar/sources/pypi.py", "PyPI source"))
    checks.append(check_file("radar/sources/npm.py", "npm source"))

    # Scoring
    print("\n🎯 Scoring Engine:")
    checks.append(check_file("radar/scoring/heuristics.py", "Heuristics"))

    # Pipeline
    print("\n🔄 Pipeline:")
    checks.append(check_file("radar/pipeline/fetch.py", "Fetch module"))
    checks.append(check_file("radar/pipeline/score.py", "Score module"))
    checks.append(check_file("radar/pipeline/feed.py", "Feed generator"))

    # Reports
    print("\n📄 Reports:")
    checks.append(check_file("radar/reports/casefile.py", "Casefile generator"))
    checks.append(check_file("radar/reports/templates/feed.md.j2", "Feed template"))
    checks.append(check_file("radar/reports/templates/casefile.md.j2", "Casefile template"))

    # Web app
    print("\n🌐 Web Application:")
    checks.append(check_file("webapp/app.py", "Streamlit app"))
    checks.append(check_file("webapp/pages/01_📈_Live_Feed.py", "Live Feed page"))
    checks.append(check_file("webapp/pages/02_🔎_Candidate_Explorer.py", "Explorer page"))
    checks.append(check_file("webapp/pages/03_📄_Casefile_Generator.py", "Casefile page"))
    checks.append(check_file("webapp/pages/04_⚙️_Settings.py", "Settings page"))

    # API
    print("\n🔌 REST API:")
    checks.append(check_file("api/main.py", "FastAPI service"))

    # Tests
    print("\n🧪 Tests:")
    checks.append(check_file("tests/test_sources_parsing.py", "Source tests"))
    checks.append(check_file("tests/test_heuristics.py", "Heuristic tests"))
    checks.append(check_file("tests/test_pipeline_end_to_end.py", "Pipeline tests"))

    # Hunt packs
    print("\n🔍 Hunt Packs:")
    checks.append(check_file("hunts/kql/slopsquat_hunts.kql", "KQL queries"))
    checks.append(check_file("hunts/kql/README.md", "KQL README"))
    checks.append(check_file("hunts/splunk/slopsquat_hunts.spl", "Splunk queries"))
    checks.append(check_file("hunts/splunk/README.md", "Splunk README"))

    # Docker
    print("\n🐳 Docker:")
    checks.append(check_file("Dockerfile.app", "App Dockerfile"))
    checks.append(check_file("Dockerfile.worker", "Worker Dockerfile"))
    checks.append(check_file("Dockerfile.api", "API Dockerfile"))
    checks.append(check_file("docker-compose.yml", "Docker Compose"))

    # CI/CD
    print("\n🤖 CI/CD:")
    checks.append(check_file(".github/workflows/radar_daily.yml", "GitHub Actions workflow"))
    checks.append(check_file(".pre-commit-config.yaml", "Pre-commit config"))

    # Config
    print("\n⚙️  Configuration:")
    checks.append(check_file("config/policy.yml", "Policy configuration"))
    checks.append(check_file("pyproject.toml", "Project config"))
    checks.append(check_file("Makefile", "Makefile"))

    # Documentation
    print("\n📚 Documentation:")
    checks.append(check_file("README.md", "README"))
    checks.append(check_file("SECURITY.md", "Security guidelines"))
    checks.append(check_file("DEPLOYMENT.md", "Deployment guide"))
    checks.append(check_file("CONTRIBUTING.md", "Contributing guide"))
    checks.append(check_file("LICENSE", "License"))

    # Sample data
    print("\n📊 Sample Data:")
    checks.append(check_file("data/samples/device_procs.csv", "Device processes CSV"))
    checks.append(check_file("data/samples/pypi_seed.jsonl", "PyPI seed data"))
    checks.append(check_file("data/samples/npm_seed.jsonl", "npm seed data"))
    checks.append(check_file("data/feeds/2024-10-16/topN.json", "Sample feed JSON"))
    checks.append(check_file("data/feeds/2024-10-16/feed.md", "Sample feed Markdown"))
    checks.append(check_file("data/feeds/2024-10-16/case_pypi_requests2.md", "Sample casefile"))

    # Directories
    print("\n📁 Directories:")
    checks.append(check_dir("data/raw", "Raw data directory"))
    checks.append(check_dir("data/processed", "Processed data directory"))
    checks.append(check_dir("data/feeds", "Feeds directory"))

    # Summary
    print("\n" + "=" * 70)
    passed = sum(checks)
    total = len(checks)
    success_rate = (passed / total) * 100

    if passed == total:
        print(f"✅ All checks passed! ({passed}/{total})")
        print("\n🚀 PhantomScan is ready to use!")
        print("   Run './quickstart.sh' to get started")
        return 0
    else:
        print(f"⚠️  Some checks failed: {passed}/{total} passed ({success_rate:.1f}%)")
        print("\n❌ Setup incomplete. Please review the missing files above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
