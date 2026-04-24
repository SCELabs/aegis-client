from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .observe import RepoObservation


def session_log_path(*, cwd: str | Path | None = None) -> Path:
    root = Path(cwd) if cwd is not None else Path.cwd()
    return root / ".aegis" / "session.jsonl"


def append_session_event(
    *,
    command: str,
    observation: RepoObservation,
    result: Any = None,
    task: str | None = None,
    cwd: str | Path | None = None,
) -> None:
    path = session_log_path(cwd=cwd)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "observation_summary": observation.summary_line(),
        "result_debug_summary": result.debug_summary() if result is not None else None,
        "task": task,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def read_recent_session_events(*, limit: int = 10, cwd: str | Path | None = None) -> list[dict[str, Any]]:
    path = session_log_path(cwd=cwd)
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if isinstance(payload, dict):
            events.append(payload)

    return events[-limit:]
