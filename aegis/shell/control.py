from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

DEFAULT_CONTROL_TTL_SECONDS = 1800


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def control_state_path(*, cwd: str | Path | None = None) -> Path:
    root = Path(cwd) if cwd is not None else Path.cwd()
    return root / ".aegis" / "control.json"


def read_control_state(*, cwd: str | Path | None = None) -> dict[str, Any] | None:
    path = control_state_path(cwd=cwd)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def write_control_state(payload: dict[str, Any], *, cwd: str | Path | None = None) -> None:
    path = control_state_path(cwd=cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def clear_control_state(*, cwd: str | Path | None = None) -> bool:
    path = control_state_path(cwd=cwd)
    if not path.exists():
        return False
    path.unlink()
    return True


def is_control_expired(state: dict[str, Any], *, now: datetime | None = None) -> bool:
    expires_at = _parse_iso(state.get("expires_at"))
    if expires_at is None:
        return False
    current = now or datetime.now(timezone.utc)
    return current >= expires_at


def _human_source_label(source: str) -> str:
    return "Aegis API" if source == "aegis_api" else "Local fallback"


def _normalize_controls(control: dict[str, Any]) -> dict[str, Any]:
    retry_limit = control.get("retry_limit", 1)
    max_files = control.get("max_files", 3)
    allow_refactor = bool(control.get("allow_refactor", False))
    require_validation = bool(control.get("require_validation", True))
    restrict_scope = bool(control.get("restrict_scope", False))
    allowed_files = control.get("allowed_files", [])
    blocked_patterns = control.get("blocked_patterns", [])
    if not isinstance(allowed_files, list):
        allowed_files = []
    if not isinstance(blocked_patterns, list):
        blocked_patterns = []
    return {
        "retry_limit": int(retry_limit) if isinstance(retry_limit, int) else 1,
        "max_files": int(max_files) if isinstance(max_files, int) else 3,
        "allow_refactor": allow_refactor,
        "require_validation": require_validation,
        "restrict_scope": restrict_scope,
        "allowed_files": allowed_files,
        "blocked_patterns": blocked_patterns,
        "validation_required": require_validation,
    }


def build_control_state(
    *,
    session_id: str,
    source: str,
    source_event: str,
    fallback: bool,
    confidence: str,
    escalation: str,
    control: dict[str, Any],
    human_controls: list[str],
    reason: str,
    ttl_seconds: int = DEFAULT_CONTROL_TTL_SECONDS,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    ttl = int(ttl_seconds) if int(ttl_seconds) > 0 else DEFAULT_CONTROL_TTL_SECONDS
    expires_at = now + timedelta(seconds=ttl)
    normalized_controls = _normalize_controls(control)
    structured_controls = {
        key: normalized_controls[key]
        for key in ["retry_limit", "max_files", "allow_refactor", "require_validation", "restrict_scope"]
    }
    return {
        "version": 1,
        "session_id": session_id,
        "updated_at": now.isoformat(),
        "source": source,
        "source_event": source_event,
        "fallback": bool(fallback),
        "confidence": confidence,
        "escalation": escalation,
        "ttl_seconds": ttl,
        "expires_at": expires_at.isoformat(),
        "controls": normalized_controls,
        "human_controls": list(human_controls),
        "structured_controls": structured_controls,
        "reason": reason,
    }


def render_control_state(*, cwd: str | Path | None = None, as_json: bool = False) -> str:
    state = read_control_state(cwd=cwd)
    if state is None:
        return "[Aegis] No active control state found."
    if as_json:
        return json.dumps(state, indent=2, sort_keys=True)

    expired = is_control_expired(state)
    controls = state.get("human_controls") or []
    if not isinstance(controls, list):
        controls = []

    source = str(state.get("source", "local_fallback"))
    status = "expired" if expired else "active"
    lines = [
        "[Aegis] Active Controls",
        f"[Aegis] Source: {_human_source_label(source)}",
        f"[Aegis] Event: {state.get('source_event', 'unknown')}",
        f"[Aegis] Confidence: {state.get('confidence', 'unknown')}",
        f"[Aegis] Escalation: {state.get('escalation', 'none')}",
        f"[Aegis] Status: {status}",
        f"[Aegis] Expires: {state.get('expires_at', 'unknown')}",
        "[Aegis] Controls:",
    ]
    if controls:
        for line in controls:
            lines.append(f"[Aegis] - {line}")
    else:
        lines.append("[Aegis] - none")
    return "\n".join(lines)


def render_control_prompt(*, cwd: str | Path | None = None) -> str:
    state = read_control_state(cwd=cwd)
    if state is None:
        return "[Aegis] No active control state found."

    controls = state.get("human_controls") or []
    if not isinstance(controls, list):
        controls = []
    lines = ["Aegis active control state:"]
    for line in controls:
        lines.append(f"- {line}")
    if is_control_expired(state):
        lines.append("")
        lines.append("Note: this control state is expired; refresh with `aegis start` if needed.")
    lines.append("")
    lines.append("Follow these controls while completing the current task. Do not expand scope unless explicitly instructed.")
    return "\n".join(lines)
