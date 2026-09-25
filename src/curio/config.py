"""Config loaders and project paths for curio."""

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
EDITIONS_DIR = PROJECT_ROOT / "editions"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_DIR = PROJECT_ROOT / "data"

load_dotenv(PROJECT_ROOT / ".env")


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f)


def load_taste() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "taste.yaml")


def load_sources() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "sources.yaml")


def load_settings() -> dict[str, Any]:
    return _read_yaml(CONFIG_DIR / "settings.yaml")
