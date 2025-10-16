"""Utility functions for PhantomScan."""

import os
from pathlib import Path
from typing import Any

import orjson
import yaml
from rich.console import Console

from radar.types import PolicyConfig

console = Console()


def load_policy() -> PolicyConfig:
    """Load policy configuration from YAML file."""
    policy_path = Path("config/policy.yml")
    if not policy_path.exists():
        raise FileNotFoundError(f"Policy file not found: {policy_path}")

    with open(policy_path) as f:
        data = yaml.safe_load(f)

    return PolicyConfig(**data)


def save_policy(policy: PolicyConfig) -> None:
    """Save policy configuration to YAML file."""
    policy_path = Path("config/policy.yml")
    with open(policy_path, "w") as f:
        yaml.dump(policy.model_dump(), f, default_flow_style=False, sort_keys=False)


def is_offline_mode() -> bool:
    """Check if offline mode is enabled via environment variable."""
    return os.environ.get("RADAR_OFFLINE", "0") == "1"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL file into list of dictionaries."""
    if not path.exists():
        return []

    data = []
    with open(path, "rb") as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(orjson.loads(line))
    return data


def save_jsonl(data: list[dict[str, Any]], path: Path) -> None:
    """Save list of dictionaries to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        for item in data:
            f.write(orjson.dumps(item))
            f.write(b"\n")


def load_json(path: Path) -> Any:
    """Load JSON file."""
    if not path.exists():
        return None

    with open(path, "rb") as f:
        return orjson.loads(f.read())


def save_json(data: Any, path: Path) -> None:
    """Save data to JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(orjson.dumps(data, option=orjson.OPT_INDENT_2))


def get_data_path(date_str: str, subdir: str) -> Path:
    """Get path for data files by date."""
    return Path("data") / subdir / date_str


def ensure_dir(path: Path) -> None:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)
