"""Central config loader. Every module reads settings from here.

Owner: Ayon
Why this exists: hardcoded magic numbers scattered across modules are the
single most common cause of irreproducible results. One YAML, one loader.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "config.yaml"
load_dotenv(ROOT / ".env")


class Config:
    """Dict-backed config with attribute access and path resolution."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def __getattr__(self, key: str) -> Any:
        try:
            val = self._data[key]
        except KeyError as exc:
            raise AttributeError(key) from exc
        return Config(val) if isinstance(val, dict) else val

    def __repr__(self) -> str:
        return f"Config({list(self._data)})"

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def to_dict(self) -> dict[str, Any]:
        return self._data

    def path(self, key: str) -> Path:
        """Resolve a key under paths: to an absolute path, creating it."""
        p = ROOT / self._data["paths"][key]
        p.mkdir(parents=True, exist_ok=True)
        return p


def load_config(path: Path | str = CONFIG_PATH) -> Config:
    with open(path) as f:
        return Config(yaml.safe_load(f))


def mlflow_uri() -> str:
    """MLflow tracking URI, with an environment override.

    Config holds the default (sqlite:///mlflow.db, next to the repo). Set
    MLFLOW_TRACKING_URI to point somewhere else - needed on machines where
    the repo lives on a network drive, because SQLite cannot lock files over
    NFS/SMB and fails with "disk I/O error".
    """
    return os.environ.get("MLFLOW_TRACKING_URI", CFG.mlflow.tracking_uri)


def firms_key() -> str:
    """Read the FIRMS API key from the environment.

    Never hardcode this. Never commit it. See .env.example.
    """
    key = os.environ.get("FIRMS_MAP_KEY")
    if not key:
        raise RuntimeError(
            "FIRMS_MAP_KEY not set. Copy .env.example to .env, add your key "
            "from https://firms.modaps.eosdis.nasa.gov/api/, then "
            "`export $(cat .env | xargs)` or use python-dotenv."
        )
    return key


CFG = load_config()
