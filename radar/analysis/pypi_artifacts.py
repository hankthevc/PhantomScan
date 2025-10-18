"""PyPI artifact analysis: sdist/wheel comparison and static scanning."""

import re
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import httpx


def fetch_latest_release_files(info_json: dict[str, Any], timeout: float = 10.0) -> list[str]:
    """Extract URLs of latest release files from PyPI JSON API response.
    
    Args:
        info_json: Full PyPI JSON API response
        timeout: Request timeout (unused here, for signature consistency)
        
    Returns:
        List of file URLs for latest release
    """
    urls = []
    
    # Get latest version
    info = info_json.get("info", {})
    latest_version = info.get("version")
    
    if not latest_version:
        return urls
    
    # Get files for latest version
    releases = info_json.get("releases", {})
    latest_files = releases.get(latest_version, [])
    
    for file_info in latest_files:
        if isinstance(file_info, dict):
            url = file_info.get("url")
            if url:
                urls.append(url)
    
    return urls


def download_and_unpack(url: str, timeout: float = 30.0) -> Path | None:
    """Download and unpack a PyPI artifact to a temporary directory.
    
    Args:
        url: URL to artifact (.tar.gz, .whl, .zip)
        timeout: HTTP request timeout in seconds
        
    Returns:
        Path to temporary directory containing unpacked files, or None on error
    """
    try:
        # Download file
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url, follow_redirects=True)
            response.raise_for_status()
        
        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="phantom_pypi_"))
        
        # Determine file type and unpack
        if url.endswith(".whl") or url.endswith(".zip"):
            # Wheel or zip file
            temp_file = temp_dir / "archive.zip"
            temp_file.write_bytes(response.content)
            
            with zipfile.ZipFile(temp_file, "r") as zf:
                zf.extractall(temp_dir)
            temp_file.unlink()
            
        elif url.endswith(".tar.gz") or url.endswith(".tgz"):
            # Source tarball
            temp_file = temp_dir / "archive.tar.gz"
            temp_file.write_bytes(response.content)
            
            with tarfile.open(temp_file, "r:gz") as tf:
                tf.extractall(temp_dir)
            temp_file.unlink()
        else:
            # Unknown format
            return None
        
        return temp_dir
        
    except Exception:
        return None


def compare_sdist_wheel(sdist_dir: Path | None, wheel_dir: Path | None) -> tuple[bool, list[str]]:
    """Compare sdist and wheel for discrepancies.
    
    Args:
        sdist_dir: Path to unpacked sdist
        wheel_dir: Path to unpacked wheel
        
    Returns:
        Tuple of (has_mismatch, list of reasons)
    """
    reasons = []
    
    if not sdist_dir or not wheel_dir:
        return False, reasons
    
    if not sdist_dir.exists() or not wheel_dir.exists():
        return False, reasons
    
    # Get Python files from both
    sdist_py_files = set()
    wheel_py_files = set()
    
    try:
        for py_file in sdist_dir.rglob("*.py"):
            # Normalize relative path
            rel_path = py_file.relative_to(sdist_dir)
            # Skip common test/doc directories
            if not any(part.startswith(("test", "doc", "example")) for part in rel_path.parts):
                sdist_py_files.add(rel_path.name)
        
        for py_file in wheel_dir.rglob("*.py"):
            rel_path = py_file.relative_to(wheel_dir)
            if not any(part.startswith(("test", "doc", "example")) for part in rel_path.parts):
                wheel_py_files.add(rel_path.name)
        
        # Check for files in wheel but not in sdist (injected code?)
        extra_in_wheel = wheel_py_files - sdist_py_files
        if extra_in_wheel:
            reasons.append(f"Wheel contains {len(extra_in_wheel)} Python files not in sdist")
            return True, reasons
        
        # Check for significant size differences in common files
        # (This is a simplified heuristic)
        
    except Exception:
        # Comparison failed, be safe
        pass
    
    return False, reasons


def static_scan(temp_dir: Path | None) -> tuple[float, list[str]]:
    """Perform static analysis scan on unpacked artifact.
    
    Args:
        temp_dir: Path to unpacked artifact
        
    Returns:
        Tuple of (risk_score 0.0-1.0, list of reasons)
    """
    if not temp_dir or not temp_dir.exists():
        return 0.0, []
    
    reasons = []
    hit_count = 0
    
    # Patterns to search for
    dangerous_patterns = [
        (r"base64\.b64decode", "Base64 decode (possible obfuscation)"),
        (r"\bexec\s*\(", "exec() call (code execution)"),
        (r"\beval\s*\(", "eval() call (code execution)"),
        (r"__import__\s*\(\s*['\"]os['\"]", "Dynamic os import"),
        (r"subprocess\.(call|run|Popen)", "Subprocess execution"),
        (r"requests\.(get|post)\s*\(", "HTTP requests (data exfiltration?)"),
        (r"urllib\.request", "URL requests (data exfiltration?)"),
        (r"socket\.socket", "Socket creation (network activity)"),
        (r"open\s*\([^)]*['\"]w", "File writing"),
        (r"os\.system", "os.system() call"),
        (r"commands\.(getoutput|getstatusoutput)", "Shell command execution"),
    ]
    
    setup_py_patterns = [
        (r"import\s+os", "OS module import in setup.py"),
        (r"import\s+subprocess", "Subprocess import in setup.py"),
        (r"download_url\s*=", "download_url in setup.py"),
    ]
    
    try:
        # Scan Python files
        for py_file in temp_dir.rglob("*.py"):
            try:
                content = py_file.read_text(errors="ignore")
                
                # Check if this is setup.py
                is_setup = py_file.name == "setup.py"
                patterns = setup_py_patterns if is_setup else dangerous_patterns
                
                for pattern, description in patterns:
                    if re.search(pattern, content):
                        hit_count += 1
                        file_rel = py_file.relative_to(temp_dir)
                        reasons.append(f"{description} in {file_rel}")
            except Exception:
                continue
        
        # Check for entry_points that might shell out
        for file in temp_dir.rglob("entry_points.txt"):
            try:
                content = file.read_text(errors="ignore")
                if "sh" in content or "bash" in content or "cmd" in content:
                    hit_count += 1
                    reasons.append("Entry point with shell command")
            except Exception:
                continue
        
    except Exception:
        pass
    
    # Compute risk score with diminishing returns
    risk_score = min(1.0, hit_count * 0.12)
    
    return risk_score, reasons


def cleanup_temp_dir(temp_dir: Path | None) -> None:
    """Clean up temporary directory.
    
    Args:
        temp_dir: Path to temporary directory to remove
    """
    if temp_dir and temp_dir.exists():
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception:
            pass
