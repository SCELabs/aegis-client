from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ENV_API_KEY = "AEGIS_API_KEY"
ENV_BASE_URL = "AEGIS_BASE_URL"
DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def default_user_config_path() -> Path:
    return Path.home() / ".aegis" / "config.json"


def load_user_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or default_user_config_path()
    if not config_path.exists():
        return {}

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    return payload if isinstance(payload, dict) else {}


def write_user_config(*, api_key: str, base_url: str, path: Path | None = None) -> Path:
    config_path = path or default_user_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"api_key": api_key, "base_url": base_url.rstrip("/")}
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return config_path


def resolve_runtime_config(path: Path | None = None) -> dict[str, str | None]:
    persisted = load_user_config(path=path)

    api_key = os.getenv(ENV_API_KEY) or persisted.get("api_key")
    base_url = os.getenv(ENV_BASE_URL) or persisted.get("base_url") or DEFAULT_BASE_URL

    return {"api_key": api_key, "base_url": str(base_url).rstrip("/")}
