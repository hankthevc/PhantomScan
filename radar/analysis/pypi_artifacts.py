"""PyPI artifact analysis for malicious code detection."""

import io
import os
import re
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import httpx

from radar.utils import is_offline_mode, load_policy


# Dangerous patterns in Python code
DANGEROUS_PATTERNS = [
    # Code execution
    (r'\bexec\s*\(', "Uses exec() for code execution"),
    (r'\beval\s*\(', "Uses eval() for code evaluation"),
    (r'\bcompile\s*\(', "Dynamically compiles code"),
    (r'\b__import__\s*\(', "Dynamic import"),
    
    # Network access with suspicious context
    (r'requests\.(?:get|post)\s*\([^)]*(?:token|password|key|secret)', "Sends credentials over network"),
    (r'urllib\.request\.urlopen\s*\([^)]*(?:token|password|key|secret)', "Sends credentials over network"),
    (r'http\.client\.[A-Z]', "Low-level HTTP client usage"),
    
    # Base64 encoding (potential obfuscation)
    (r'base64\.b64decode\s*\(', "Base64 decoding (potential obfuscation)"),
    (r'base64\.decodebytes\s*\(', "Base64 decoding"),
    
    # Process execution
    (r'subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True', "Shell command execution"),
    (r'os\.system\s*\(', "OS command execution"),
    (r'os\.popen\s*\(', "OS popen execution"),
    
    # File operations in suspicious locations
    (r'open\s*\([^)]*[\'"](?:/etc/|/root/|\.ssh/|\.aws/)', "Accesses sensitive system directories"),
    
    # Credential harvesting
    (r'(?:password|passwd|token|secret|api[_-]?key)\s*=\s*os\.(?:environ|getenv)', "Reads credentials from environment"),
    
    # Unusual setup.py patterns
    (r'setup\s*\([^)]*cmdclass\s*=', "Custom command classes in setup.py"),
    (r'setup\s*\([^)]*install_requires.*(?:exec|eval)', "Suspicious install_requires"),
]

COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE | re.MULTILINE), reason) for pattern, reason in DANGEROUS_PATTERNS]


# Suspicious entry points (scripts that might execute on import)
SUSPICIOUS_ENTRY_PATTERNS = [
    (r'console_scripts.*=.*:.*system', "Entry point calls system"),
    (r'console_scripts.*=.*:.*exec', "Entry point uses exec"),
]

COMPILED_ENTRY_PATTERNS = [(re.compile(pattern, re.IGNORECASE), reason) for pattern, reason in SUSPICIOUS_ENTRY_PATTERNS]


def fetch_latest_release_files(info_json: dict[str, Any]) -> list[str]:
    """Extract download URLs from PyPI JSON response.

    Args:
        info_json: PyPI JSON API response

    Returns:
        List of download URLs for latest release
    """
    urls = info_json.get("urls", [])
    return [item["url"] for item in urls if "url" in item]


def download_and_unpack(url: str, timeout: int = 30) -> Path | None:
    """Download and unpack a package artifact.

    Args:
        url: Download URL
        timeout: Request timeout in seconds

    Returns:
        Path to unpacked directory, or None on failure
    """
    if is_offline_mode():
        return None

    try:
        policy = load_policy()
        user_agent = policy.network.get("user_agent", "PhantomScan/0.1.0")
        
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": user_agent})
            response.raise_for_status()

        # Create temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="phantomscan_"))

        # Determine file type and unpack
        content = response.content
        
        if url.endswith(".tar.gz") or url.endswith(".tgz"):
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
                # Security: Check for path traversal
                for member in tar.getmembers():
                    if member.name.startswith("/") or ".." in member.name:
                        continue
                    tar.extract(member, temp_dir)
        
        elif url.endswith(".whl") or url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                # Security: Check for path traversal
                for name in zf.namelist():
                    if name.startswith("/") or ".." in name:
                        continue
                    zf.extract(name, temp_dir)
        
        else:
            # Unsupported format
            return None

        return temp_dir

    except Exception:
        # Fail gracefully
        return None


def compare_sdist_wheel(sdist_dir: Path | None, wheel_dir: Path | None) -> tuple[bool, list[str]]:
    """Compare source distribution vs wheel for discrepancies.

    Args:
        sdist_dir: Unpacked sdist directory
        wheel_dir: Unpacked wheel directory

    Returns:
        Tuple of (has_mismatch, reasons)
    """
    if not sdist_dir or not wheel_dir:
        return False, []

    reasons = []
    has_mismatch = False

    try:
        # Get Python files from both
        sdist_py_files = set()
        wheel_py_files = set()

        for py_file in sdist_dir.rglob("*.py"):
            rel_path = py_file.relative_to(sdist_dir)
            # Skip common directories
            if any(part in ["tests", "test", "docs", "examples"] for part in rel_path.parts):
                continue
            sdist_py_files.add(str(rel_path))

        for py_file in wheel_dir.rglob("*.py"):
            rel_path = py_file.relative_to(wheel_dir)
            if any(part in ["tests", "test", "docs", "examples"] for part in rel_path.parts):
                continue
            wheel_py_files.add(str(rel_path))

        # Check for files only in wheel (suspicious - added during build)
        wheel_only = wheel_py_files - sdist_py_files
        if wheel_only:
            has_mismatch = True
            reasons.append(f"Wheel contains {len(wheel_only)} files not in sdist")

        # Check for setup.py differences (if it's executed during build)
        sdist_setup = sdist_dir / "setup.py"
        if sdist_setup.exists():
            with open(sdist_setup, "r", encoding="utf-8", errors="ignore") as f:
                setup_content = f.read()
                # Check for code execution during setup
                if re.search(r'\bexec\s*\(', setup_content) or re.search(r'\beval\s*\(', setup_content):
                    has_mismatch = True
                    reasons.append("setup.py contains exec/eval (may inject code during build)")

    except Exception:
        # Fail gracefully
        pass

    return has_mismatch, reasons


def static_scan(temp_dir: Path | None) -> tuple[float, list[str]]:
    """Perform static analysis on unpacked package.

    Args:
        temp_dir: Directory containing unpacked package

    Returns:
        Tuple of (risk_score, reasons)
    """
    if not temp_dir or not temp_dir.exists():
        return 0.0, []

    reasons = []
    hit_count = 0

    try:
        # Scan all Python files
        for py_file in temp_dir.rglob("*.py"):
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Check dangerous patterns
                for pattern, reason in COMPILED_PATTERNS:
                    if pattern.search(content):
                        hit_count += 1
                        rel_path = py_file.relative_to(temp_dir)
                        reasons.append(f"{rel_path}: {reason}")
                        break  # One reason per file

            except Exception:
                continue

        # Check setup.py for entry points
        setup_py = temp_dir / "setup.py"
        if setup_py.exists():
            try:
                with open(setup_py, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    for pattern, reason in COMPILED_ENTRY_PATTERNS:
                        if pattern.search(content):
                            hit_count += 1
                            reasons.append(f"setup.py: {reason}")
            except Exception:
                pass

        # Check for __init__.py with immediate execution
        for init_file in temp_dir.rglob("__init__.py"):
            try:
                with open(init_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    # Check if __init__ has substantive code (not just imports)
                    lines = [
                        line.strip()
                        for line in content.split("\n")
                        if line.strip() and not line.strip().startswith("#")
                    ]
                    non_import_lines = [
                        line
                        for line in lines
                        if not line.startswith(("import ", "from "))
                        and not line.startswith("__")  # Skip __version__, __all__, etc.
                    ]
                    
                    if len(non_import_lines) > 5:
                        # Significant code in __init__ - might execute on import
                        if any(
                            keyword in content
                            for keyword in ["exec(", "eval(", "os.system", "subprocess"]
                        ):
                            hit_count += 1
                            rel_path = init_file.relative_to(temp_dir)
                            reasons.append(f"{rel_path}: Executes code on import")
            except Exception:
                continue

    except Exception:
        pass

    # Compute risk score with diminishing returns
    risk_score = min(hit_count / 10.0, 1.0)

    return risk_score, reasons


def cleanup_tempdir(temp_dir: Path | None) -> None:
    """Safely remove temporary directory.

    Args:
        temp_dir: Directory to remove
    """
    if not temp_dir or not temp_dir.exists():
        return

    try:
        import shutil
        shutil.rmtree(temp_dir)
    except Exception:
        pass
