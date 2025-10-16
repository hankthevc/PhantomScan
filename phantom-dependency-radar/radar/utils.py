"""Utility functions for the Phantom Dependency Radar."""

import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import orjson
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .types import PolicyConfig

console = Console()


def load_policy(config_path: Optional[Path] = None) -> PolicyConfig:
    """Load policy configuration from YAML file."""
    if config_path is None:
        config_path = Path("config/policy.yml")
    
    if not config_path.exists():
        console.print(f"[yellow]Warning: Policy file {config_path} not found, using defaults[/yellow]")
        return PolicyConfig()
    
    try:
        with open(config_path, 'r') as f:
            data = yaml.safe_load(f)
        return PolicyConfig(**data)
    except Exception as e:
        console.print(f"[red]Error loading policy from {config_path}: {e}[/red]")
        console.print("[yellow]Using default policy configuration[/yellow]")
        return PolicyConfig()


def save_policy(policy: PolicyConfig, config_path: Optional[Path] = None) -> None:
    """Save policy configuration to YAML file."""
    if config_path is None:
        config_path = Path("config/policy.yml")
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict and clean up for YAML
    data = policy.dict()
    
    with open(config_path, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def is_offline_mode() -> bool:
    """Check if running in offline mode."""
    return os.getenv("RADAR_OFFLINE", "").lower() in ("1", "true", "yes")


def safe_filename(name: str) -> str:
    """Convert package name to safe filename."""
    # Replace problematic characters
    safe = name.replace("/", "_").replace("@", "_at_").replace(".", "_")
    return safe


def ensure_data_dirs() -> None:
    """Ensure all required data directories exist."""
    dirs = [
        "data/raw",
        "data/processed", 
        "data/feeds",
        "data/samples"
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)


def load_json(file_path: Path) -> Any:
    """Load JSON data from file using orjson."""
    try:
        with open(file_path, 'rb') as f:
            return orjson.loads(f.read())
    except FileNotFoundError:
        console.print(f"[red]File not found: {file_path}[/red]")
        return None
    except orjson.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in {file_path}: {e}[/red]")
        return None


def save_json(data: Any, file_path: Path, pretty: bool = False) -> None:
    """Save data to JSON file using orjson."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    options = orjson.OPT_INDENT_2 if pretty else 0
    
    with open(file_path, 'wb') as f:
        f.write(orjson.dumps(data, option=options))


def load_jsonl(file_path: Path) -> list:
    """Load JSONL (JSON Lines) data from file."""
    if not file_path.exists():
        return []
    
    data = []
    try:
        with open(file_path, 'rb') as f:
            for line in f:
                line = line.strip()
                if line:
                    data.append(orjson.loads(line))
    except Exception as e:
        console.print(f"[red]Error loading JSONL from {file_path}: {e}[/red]")
        return []
    
    return data


def save_jsonl(data: list, file_path: Path) -> None:
    """Save data to JSONL (JSON Lines) file."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'wb') as f:
        for item in data:
            f.write(orjson.dumps(item))
            f.write(b'\n')


def create_http_client(timeout: float = 30.0, retries: int = 3) -> httpx.Client:
    """Create configured HTTP client with retries."""
    policy = load_policy()
    user_agent = policy.dict().get("network", {}).get("user_agent", "PhantomDependencyRadar/0.1.0")
    
    return httpx.Client(
        timeout=timeout,
        headers={"User-Agent": user_agent},
        follow_redirects=True
    )


def retry_on_failure(func, max_attempts: int = 3, delay: float = 1.0):
    """Retry decorator for network operations."""
    def wrapper(*args, **kwargs):
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise e
                console.print(f"[yellow]Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...[/yellow]")
                time.sleep(delay)
    return wrapper


def format_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis if too long."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


class ProgressReporter:
    """Progress reporter for long-running operations."""
    
    def __init__(self, description: str):
        self.description = description
        self.progress = None
        self.task = None
    
    def __enter__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        )
        self.progress.start()
        self.task = self.progress.add_task(self.description, total=None)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.progress:
            self.progress.stop()
    
    def update(self, description: Optional[str] = None):
        """Update progress description."""
        if self.progress and self.task and description:
            self.progress.update(self.task, description=description)


def get_date_str() -> str:
    """Get current date as YYYY-MM-DD string."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d")


def parse_date_str(date_str: str) -> str:
    """Validate and normalize date string."""
    from datetime import datetime
    try:
        # Try to parse the date to validate format
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def get_package_url(ecosystem: str, package_name: str) -> str:
    """Get the canonical URL for a package."""
    if ecosystem == "pypi":
        return f"https://pypi.org/project/{package_name}/"
    elif ecosystem == "npm":
        return f"https://www.npmjs.com/package/{package_name}"
    else:
        return ""