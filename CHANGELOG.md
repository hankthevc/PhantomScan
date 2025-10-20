# Changelog

All notable changes to PhantomScan will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **feat(pypi)**: PyPI version-flip heuristic now compares current version with most recent previous version within a rolling 30-day window (configurable via `thresholds.version_flip_window_days`)
- **feat(pypi)**: Version flip now detects dependency increases of ≥8 packages (stricter threshold) with risk score of 0.6
- **feat(pypi)**: Version flip detects new documentation/project URLs added in latest version
- **feat(api)**: `/score` endpoint timeout guard prevents long-running enrichment fan-outs
- **feat(config)**: Added `network.api_timeout_seconds` to policy.yml for tunable API timeout (default: 8 seconds)

### Changed
- Version flip dependency increase threshold reduced from 10 to 8 packages for more sensitive detection
- API timeout responses now return HTTP 503 with message "Temporary overload: scoring timed out"
- Version flip now uses time-based window comparison instead of simple sequential version comparison

### Fixed
- Version flip analysis now gracefully handles missing upload timestamps
- API timeout now reads from policy configuration instead of hardcoded value

## [0.1.0] - 2024-10-18

### Added
- Initial release with 7-dimension scoring engine
- PyPI and npm data source support
- Streamlit web UI with Live Feed, Candidate Explorer, and Quick Score Panel
- FastAPI REST API with `/score`, `/feed`, and `/casefile` endpoints
- Unit tests with >80% coverage
- Docker support
- GitHub Actions automation
