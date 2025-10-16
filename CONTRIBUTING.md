# Contributing to PhantomScan

Thank you for your interest in contributing to PhantomScan! This document provides guidelines and instructions.

## 🤝 Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Follow responsible disclosure for security issues

## 🐛 Reporting Bugs

1. Check existing issues first
2. Use the bug report template
3. Include:
   - Environment details (OS, Python version)
   - Steps to reproduce
   - Expected vs actual behavior
   - Relevant logs

## 💡 Suggesting Features

1. Open an issue with the feature request template
2. Describe:
   - Use case and motivation
   - Proposed implementation (if applicable)
   - Alternatives considered

## 🔧 Development Setup

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/phantom-dependency-radar.git
cd phantom-dependency-radar

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in development mode
make setup

# Run tests
make test

# Run linters
make lint
make type
```

## 📝 Making Changes

### Workflow

1. Create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes following the style guide

3. Write/update tests:
   ```bash
   pytest tests/
   ```

4. Ensure code quality:
   ```bash
   make lint
   make type
   ```

5. Commit with descriptive messages:
   ```bash
   git commit -m "feat: add new heuristic for X"
   ```

6. Push and create a pull request

### Commit Message Format

Follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Test additions or changes
- `refactor:` - Code refactoring
- `chore:` - Maintenance tasks

Examples:
```
feat: add fuzzy matching for package names
fix: handle missing repository URL gracefully
docs: update installation instructions
test: add unit tests for npm parser
```

## 🎨 Style Guide

### Python

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Use ruff and black (run `make lint`)

Example:
```python
def score_package(candidate: PackageCandidate) -> float:
    """Compute risk score for a package.

    Args:
        candidate: Package candidate to score

    Returns:
        Risk score between 0.0 and 1.0
    """
    # Implementation
    pass
```

### Documentation

- Docstrings for all public functions/classes
- README updates for new features
- Inline comments for complex logic

## 🧪 Testing

### Writing Tests

- Place tests in `tests/` directory
- Name files `test_*.py`
- Use descriptive test names
- Aim for >80% code coverage

Example:
```python
def test_score_suspicious_package(scorer: PackageScorer) -> None:
    """Test that obvious slopsquats get high scores."""
    package = PackageCandidate(
        ecosystem=Ecosystem.PYPI,
        name="requests2",
        version="0.0.1",
        created_at=datetime.now(timezone.utc),
        maintainers_count=1,
    )

    breakdown = scorer.score(package)
    assert breakdown.name_suspicion > 0.5
```

### Running Tests

```bash
# All tests
make test

# Specific test file
pytest tests/test_heuristics.py

# With coverage
pytest --cov=radar --cov-report=html
```

## 📚 Documentation

Update documentation when:
- Adding new features
- Changing APIs
- Modifying configuration
- Adding new dependencies

Documentation locations:
- `README.md` - Overview and quick start
- `DEPLOYMENT.md` - Deployment instructions
- `SECURITY.md` - Security guidelines
- Docstrings - Code-level documentation

## 🔒 Security

**Do not** open public issues for security vulnerabilities.

Instead:
1. Email security@example.com (replace with actual)
2. Include:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
3. Allow 48 hours for initial response

## 🎯 Areas for Contribution

High-impact areas:

1. **New Heuristics**:
   - Improve name suspicion detection
   - Add ecosystem-specific signals
   - ML-based scoring (optional)

2. **Data Sources**:
   - Additional package registries (RubyGems, crates.io)
   - Alternative APIs

3. **UI Improvements**:
   - Enhanced visualizations
   - Mobile responsiveness
   - Dark mode

4. **Hunt Packs**:
   - Additional SIEM queries
   - Detection improvements

5. **Testing**:
   - Increase coverage
   - Integration tests
   - Performance tests

## 📋 Pull Request Checklist

Before submitting:

- [ ] Tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make type`)
- [ ] Documentation updated
- [ ] CHANGELOG updated (if applicable)
- [ ] PR description explains changes
- [ ] Linked to related issues

## 🔄 Review Process

1. Automated checks run on PR
2. Maintainer reviews code
3. Address feedback
4. Approval and merge

Typical timeline: 2-5 business days

## 🏆 Recognition

Contributors are recognized in:
- CONTRIBUTORS.md file
- Release notes
- GitHub contributor graph

Thank you for helping make PhantomScan better! 🎉
