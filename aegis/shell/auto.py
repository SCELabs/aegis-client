from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from aegis import AegisClient

from .config import (
    DEFAULT_BASE_URL,
    ENV_API_KEY,
    ENV_BASE_URL,
    default_user_config_path,
    load_user_config,
    resolve_runtime_config,
)
from .control import build_control_state, is_control_expired, read_control_state, write_control_state
from .observe import RepoObservation, collect_repo_observation
from .session import append_auto_event, read_all_session_events, session_log_path

CALL_COST_USD = 0.20
DEFAULT_INTERVAL_SECONDS = 3.0
DEFAULT_SCOPE_FILE_THRESHOLD = 5
DEFAULT_SCOPE_SPIKE_THRESHOLD = 3
DIFF_GROWTH_MULTIPLIER = 1.5
NO_ISSUES_FEEDBACK_SECONDS = 10.0
ESCALATION_STATUS_INTERVAL_SECONDS = 8.0
HEARTBEAT_STALE_SECONDS = 15.0


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class DiffSnapshot:
    files_changed: int
    changed_file_count: int
    insertions: int
    deletions: int

    @property
    def signature(self) -> tuple[int, int, int, int]:
        return (
            self.files_changed,
            self.changed_file_count,
            self.insertions,
            self.deletions,
        )

    @property
    def has_changes(self) -> bool:
        return any(value > 0 for value in self.signature)

    def to_dict(self) -> dict[str, int]:
        return {
            "files_changed": self.files_changed,
            "changed_file_count": self.changed_file_count,
            "insertions": self.insertions,
            "deletions": self.deletions,
        }


@dataclass(slots=True)
class SignalCandidate:
    signal_type: str
    severity_candidate: str
    message: str
    local_suggestion: str
    estimated_calls_avoided: int
    details: dict[str, Any]

    @property
    def estimated_cost_saved(self) -> float:
        return round(self.estimated_calls_avoided * CALL_COST_USD, 2)


@dataclass(slots=True)
class AutoMetrics:
    duration_minutes: int
    loop_signals: int
    scope_drift_signals: int
    diff_growth_signals: int
    local_signal_count: int
    aegis_decision_count: int
    local_fallback_count: int
    escalation_count: int
    retries_avoided: int
    estimated_calls_saved: int
    estimated_cost_saved: float
    notes: list[str]
    session_count: int = 1


@dataclass(slots=True)
class DecisionOutcome:
    full_output: str
    minimal_output: str
    signal_type: str
    escalation: str
    confidence: str
    state_fingerprint: tuple[Any, ...]


def _signal_label(signal_type: str) -> str:
    if signal_type == "loop_signal":
        return "Loop detected"
    if signal_type == "scope_drift_signal":
        return "Scope drift detected"
    if signal_type == "diff_growth_signal":
        return "Large change detected"
    return "Issue detected"


class AutoHeuristicEngine:
    def __init__(
        self,
        *,
        scope_file_threshold: int = DEFAULT_SCOPE_FILE_THRESHOLD,
        scope_spike_threshold: int = DEFAULT_SCOPE_SPIKE_THRESHOLD,
    ) -> None:
        self.scope_file_threshold = scope_file_threshold
        self.scope_spike_threshold = scope_spike_threshold
        self._previous: DiffSnapshot | None = None
        self._same_signature_streak = 1
        self._loop_active = False
        self._scope_active = False
        self._growth_active = False

    @property
    def previous_snapshot(self) -> DiffSnapshot | None:
        return self._previous

    def evaluate(self, observation: RepoObservation) -> list[SignalCandidate]:
        snapshot = DiffSnapshot(
            files_changed=int(observation.diff_summary.get("files_changed", 0)),
            changed_file_count=observation.changed_file_count,
            insertions=int(observation.diff_summary.get("insertions", 0)),
            deletions=int(observation.diff_summary.get("deletions", 0)),
        )
        signals: list[SignalCandidate] = []

        if self._previous is not None:
            activity_detected = snapshot.signature != self._previous.signature
            if snapshot.signature == self._previous.signature and snapshot.has_changes:
                self._same_signature_streak += 1
            else:
                self._same_signature_streak = 1
                self._loop_active = False

            if self._same_signature_streak >= 3 and not self._loop_active:
                signals.append(
                    SignalCandidate(
                        signal_type="loop_signal",
                        severity_candidate="medium",
                        message=f"Loop detected (no change in diff across {self._same_signature_streak} cycles)",
                        local_suggestion="Stop retries and inspect the failure before continuing.",
                        estimated_calls_avoided=3,
                        details={
                            "cycles": self._same_signature_streak,
                            "activity_detected": activity_detected,
                        },
                    )
                )
                self._loop_active = True

            file_growth = snapshot.changed_file_count - self._previous.changed_file_count
            scope_triggered = (
                snapshot.changed_file_count > self.scope_file_threshold
                or file_growth > self.scope_spike_threshold
            )
            if scope_triggered and not self._scope_active:
                severity = "high" if snapshot.changed_file_count > self.scope_file_threshold + 2 else "medium"
                signals.append(
                    SignalCandidate(
                        signal_type="scope_drift_signal",
                        severity_candidate=severity,
                        message=(
                            "Scope drift detected "
                            f"(file count increased from {self._previous.changed_file_count} -> "
                            f"{snapshot.changed_file_count})"
                        ),
                        local_suggestion="Pause and tighten task boundaries before adding more files.",
                        estimated_calls_avoided=7,
                        details={
                            "changed_files": snapshot.changed_file_count,
                            "file_growth": file_growth,
                            "activity_detected": activity_detected,
                        },
                    )
                )
                self._scope_active = True
            if not scope_triggered:
                self._scope_active = False

            prior_insertions = self._previous.insertions
            growth_triggered = (
                prior_insertions > 0
                and snapshot.insertions > int(prior_insertions * DIFF_GROWTH_MULTIPLIER)
            )
            if growth_triggered and not self._growth_active:
                growth_ratio = snapshot.insertions / prior_insertions
                growth_percent = int((growth_ratio - 1.0) * 100)
                severity = "high" if growth_ratio >= 2 else "medium"
                signals.append(
                    SignalCandidate(
                        signal_type="diff_growth_signal",
                        severity_candidate=severity,
                        message=f"Large change detected (insertions increased {growth_percent}%)",
                        local_suggestion="Split the change into smaller checkpoints and validate incrementally.",
                        estimated_calls_avoided=6,
                        details={
                            "prior_insertions": prior_insertions,
                            "current_insertions": snapshot.insertions,
                            "growth_ratio": round(growth_ratio, 2),
                            "activity_detected": activity_detected,
                        },
                    )
                )
                self._growth_active = True
            if not growth_triggered:
                self._growth_active = False

        self._previous = snapshot
        return signals


def _auto_state_path(*, cwd: str | Path | None = None) -> Path:
    root = Path(cwd) if cwd is not None else Path.cwd()
    return root / ".aegis" / "auto_state.json"


def _project_runtime_dir(*, cwd: str | Path | None = None) -> Path:
    root = Path(cwd) if cwd is not None else Path.cwd()
    return root / ".aegis"


def read_auto_state(*, cwd: str | Path | None = None) -> dict[str, Any]:
    path = _auto_state_path(cwd=cwd)
    if not path.exists():
        return {"running": False}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return {"running": False}
    if not isinstance(payload, dict):
        return {"running": False}
    return payload


def write_auto_state(payload: dict[str, Any], *, cwd: str | Path | None = None) -> None:
    path = _auto_state_path(cwd=cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _is_git_repo(*, cwd: str | Path | None = None) -> bool:
    repo_cwd = str(Path(cwd) if cwd is not None else Path.cwd())
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=repo_cwd,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return proc.returncode == 0 and (proc.stdout or "").strip().lower() == "true"


def _is_pid_running(pid: int) -> bool | None:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except OSError:
        return None


def _runtime_config_sources() -> tuple[dict[str, str | None], dict[str, str], Path, bool]:
    config_path = default_user_config_path()
    persisted = load_user_config(path=config_path)
    config_found = config_path.exists()

    env_api = os.getenv(ENV_API_KEY) or ""
    env_base = os.getenv(ENV_BASE_URL) or ""
    api_source = "env" if env_api else ("config" if persisted.get("api_key") else "missing")
    if env_base:
        base_source = "env"
    elif persisted.get("base_url"):
        base_source = "config"
    else:
        base_source = "default"

    runtime = resolve_runtime_config(path=config_path if config_found else None)
    return runtime, {"api_key": api_source, "base_url": base_source}, config_path, config_found


def _backend_reachable(*, base_url: str | None, api_key: str | None) -> str:
    if not api_key:
        return "unknown"
    if not base_url:
        return "unknown"
    try:
        requests.get(str(base_url).rstrip("/"), timeout=2.0)
        return "yes"
    except requests.RequestException:
        return "no"


def preflight_check(*, cwd: str | Path | None = None, print_messages: bool = True) -> dict[str, Any]:
    runtime_dir = _project_runtime_dir(cwd=cwd)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    state = read_auto_state(cwd=cwd)
    if state.get("stop_requested"):
        state["stop_requested"] = False
        state.pop("stop_requested_at", None)
        write_auto_state(state, cwd=cwd)

    runtime, sources, _, _ = _runtime_config_sources()
    messages: list[str] = []
    can_run = True
    if not runtime.get("api_key"):
        messages.append("[Aegis] No API key found. Run `aegis init` or set AEGIS_API_KEY.")

    if not _is_git_repo(cwd=cwd):
        messages.append("[Aegis] No git repo detected. Run this inside a project directory.")
        can_run = False

    backend = _backend_reachable(base_url=runtime.get("base_url"), api_key=runtime.get("api_key"))
    if backend == "no":
        messages.append("[Aegis] API unavailable — local monitoring still active.")

    if print_messages:
        for message in messages:
            print(message)

    return {
        "can_run": can_run,
        "messages": messages,
        "backend_reachable": backend,
        "runtime_sources": sources,
    }


def stop_auto_mode(*, cwd: str | Path | None = None) -> bool:
    state = read_auto_state(cwd=cwd)
    was_running = bool(state.get("running"))
    state["stop_requested"] = True
    state["stop_requested_at"] = _utc_now_iso()
    if "running" not in state:
        state["running"] = False
    write_auto_state(state, cwd=cwd)
    return was_running


def start_auto_mode_background(
    *,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    verbose: bool = False,
    cwd: str | Path | None = None,
) -> int:
    preflight = preflight_check(cwd=cwd, print_messages=True)
    if not preflight.get("can_run"):
        return 1

    state = read_auto_state(cwd=cwd)
    if state.get("running") and not state.get("stop_requested"):
        print("[Aegis] Auto mode is already running.")
        return 0

    repo_cwd = str(Path(cwd) if cwd is not None else Path.cwd())
    command = [
        sys.executable,
        "-m",
        "aegis.shell.cli",
        "auto",
        "--interval",
        str(max(2.0, min(interval_seconds, 5.0))),
        "--background-worker",
    ]
    if verbose:
        command.append("--verbose")

    try:
        kwargs: dict[str, Any] = {
            "cwd": repo_cwd,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
            "stdin": subprocess.DEVNULL,
            "close_fds": True,
        }
        if os.name == "nt":
            flags = 0
            no_window_flag = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if no_window_flag:
                flags |= no_window_flag
                flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            else:
                flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
                flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            kwargs["creationflags"] = flags
        else:
            kwargs["start_new_session"] = True
        proc = subprocess.Popen(command, **kwargs)
    except Exception:
        print("[Aegis] Background start is unavailable here. Run `aegis auto` in a terminal instead.")
        return 1

    if proc.poll() is not None:
        print("[Aegis] Background start is unavailable here. Run `aegis auto` in a terminal instead.")
        return 1

    now = _utc_now_iso()
    write_auto_state(
        {
            "running": True,
            "stop_requested": False,
            "mode": "background",
            "pid": proc.pid,
            "started_at": now,
            "last_heartbeat_at": now,
            "interval_seconds": max(2.0, min(interval_seconds, 5.0)),
            "project_path": repo_cwd,
        },
        cwd=cwd,
    )
    print("[Aegis] Auto mode started in background.")
    print("[Aegis] Run `aegis status`, `aegis summary`, or `aegis stop`.")
    return 0


def render_doctor(*, cwd: str | Path | None = None) -> str:
    repo_path = str(Path(cwd) if cwd is not None else Path.cwd())
    runtime, sources, config_path, config_found = _runtime_config_sources()
    git_detected = _is_git_repo(cwd=cwd)
    runtime_dir = _project_runtime_dir(cwd=cwd)
    backend = _backend_reachable(base_url=runtime.get("base_url"), api_key=runtime.get("api_key"))
    state = read_auto_state(cwd=cwd)
    running_state = "yes" if state.get("running") else "no"
    pid = state.get("pid")
    pid_text = str(pid) if isinstance(pid, int) else "none"

    lines = [
        "[Aegis] Doctor",
        f"[Aegis] Config path: {config_path}",
        f"[Aegis] Config found: {'yes' if config_found else 'no'}",
        f"[Aegis] API key source: {sources['api_key']}",
        f"[Aegis] Base URL source: {sources['base_url']}",
        f"[Aegis] Current repo path: {repo_path}",
        f"[Aegis] Git repo detected: {'yes' if git_detected else 'no'}",
        f"[Aegis] Project .aegis path: {runtime_dir}",
        f"[Aegis] Backend reachable: {backend}",
        f"[Aegis] Current auto status: {running_state}",
        f"[Aegis] Mode: {state.get('mode', 'unknown')}",
        f"[Aegis] PID: {pid_text}",
    ]
    return "\n".join(lines)


def reset_project_runtime(*, cwd: str | Path | None = None) -> str:
    runtime_dir = _project_runtime_dir(cwd=cwd)
    if runtime_dir.exists():
        shutil.rmtree(runtime_dir, ignore_errors=True)
    return f"[Aegis] Reset project runtime state at {runtime_dir}"


def _build_client() -> AegisClient:
    runtime = resolve_runtime_config()
    return AegisClient(
        api_key=runtime.get("api_key"),
        base_url=runtime.get("base_url"),
    )


def _build_signal_payload(
    *,
    observation: RepoObservation,
    signal: SignalCandidate,
    previous_snapshot: DiffSnapshot | None,
    session_id: str,
) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "signal_type": signal.signal_type,
        "severity_candidate": signal.severity_candidate,
        "repo_observation": observation.to_dict(),
        "previous_snapshot": previous_snapshot.to_dict() if previous_snapshot is not None else None,
        "signal_details": signal.details,
        "local_suggestion": signal.local_suggestion,
        "estimated_calls_avoided": signal.estimated_calls_avoided,
        "estimated_cost_saved": signal.estimated_cost_saved,
    }


def _aegis_decision_for_signal(
    *,
    client: AegisClient,
    payload: dict[str, Any],
    signal: SignalCandidate,
) -> tuple[dict[str, Any], bool]:
    try:
        result = client.auto().step(
            step_name="auto_mode_signal_control",
            step_input=payload,
            symptoms=[signal.signal_type],
            severity=signal.severity_candidate,
        )
    except Exception as exc:
        fallback = {
            "source": "local_fallback",
            "signal_type": signal.signal_type,
            "actions": [],
            "explanation": (
                f"Local fallback: Aegis API unavailable ({exc.__class__.__name__}). "
                f"{signal.local_suggestion}"
            ),
            "trace": [],
            "metrics": {"estimated_calls_saved": signal.estimated_calls_avoided},
            "scope_data": {"fallback_reason": str(exc)},
        }
        return fallback, True

    decision = {
        "source": "aegis_api",
        "signal_type": signal.signal_type,
        "actions": list(getattr(result, "actions", []) or []),
        "explanation": getattr(result, "explanation", None) or "No explanation provided.",
        "trace": list(getattr(result, "trace", []) or []),
        "metrics": dict(getattr(result, "metrics", {}) or {}),
        "scope_data": dict(getattr(result, "scope_data", {}) or {}),
    }
    return decision, False


def _impact_range(signal_type: str) -> tuple[int, int]:
    if signal_type == "loop_signal":
        return 2, 4
    if signal_type == "scope_drift_signal":
        return 5, 10
    if signal_type == "diff_growth_signal":
        return 4, 8
    return 2, 4


def _escalation_level(same_issue_count: int) -> str:
    if same_issue_count >= 3:
        return "high"
    if same_issue_count >= 2:
        return "medium"
    return "none"


def _confidence_label(same_issue_count: int) -> str:
    return "high" if same_issue_count >= 2 else "moderate"


def _derive_control(*, actions: list[dict[str, Any]], signal: SignalCandidate) -> dict[str, Any]:
    control: dict[str, Any] = {
        "retry_limit": 1,
        "max_files": 3,
        "allow_refactor": False,
        "require_validation": True,
    }
    if signal.signal_type == "scope_drift_signal":
        control["max_files"] = 3
    if signal.signal_type == "diff_growth_signal":
        control["max_files"] = 3
        control["require_validation"] = True

    for action in actions:
        action_type = str(action.get("type", "")).strip().lower()
        if action_type == "stabilize_system":
            control["retry_limit"] = 1
            control["require_validation"] = True
        elif action_type == "reduce_variability":
            control["max_files"] = min(int(control.get("max_files", 3)), 3)
            control["allow_refactor"] = False
        elif action_type == "increase_coordination_constraints":
            control["max_files"] = min(int(control.get("max_files", 3)), 2)
            control["restrict_scope"] = True
    return control


def _control_guidance(control: dict[str, Any]) -> list[str]:
    lines = ["Stop retries"]
    max_files = control.get("max_files")
    if isinstance(max_files, int):
        if max_files <= 2:
            lines.append("Limit changes to 1-2 files")
        elif max_files <= 3:
            lines.append("Limit changes to 2-3 files")
        else:
            lines.append(f"Limit changes to {max_files} files")
    if control.get("allow_refactor") is False:
        lines.append("Avoid refactoring unrelated code")
    if control.get("require_validation"):
        lines.append("Validate changes before next step")
    if control.get("restrict_scope"):
        lines.append("Restrict scope to the current task")
    lines.append("Inspect failure directly")

    deduped: list[str] = []
    for line in lines:
        if line not in deduped:
            deduped.append(line)
    return deduped


def _render_structured_control(control: dict[str, Any]) -> list[str]:
    order = ["retry_limit", "max_files", "allow_refactor", "require_validation", "restrict_scope"]
    rendered: list[str] = []
    for key in order:
        if key not in control:
            continue
        value = control[key]
        if isinstance(value, bool):
            rendered.append(f"[Aegis] {key}: {'true' if value else 'false'}")
        else:
            rendered.append(f"[Aegis] {key}: {value}")
    return rendered


def _render_decision_output(
    *,
    signal: SignalCandidate,
    decision: dict[str, Any],
    control: dict[str, Any],
    confidence: str,
    escalation: str,
    impact_estimate: dict[str, Any],
    fallback: bool,
    show_structured_control: bool,
) -> str:
    source_label = "Local fallback" if fallback else "Aegis recommendation"
    explanation = _contextual_explanation(signal.signal_type)
    if fallback:
        explanation = f"{explanation}. Aegis API unavailable, using local control."
    lines = [
        "[Aegis]",
        f"[Aegis] {signal.message}",
        f"[Aegis] {source_label}: {explanation}",
        f"[Aegis] Control ({confidence} confidence):",
    ]
    for line in _control_guidance(control):
        lines.append(f"[Aegis] - {line}")

    if show_structured_control:
        lines.append("[Aegis] Control (structured):")
        lines.extend(_render_structured_control(control))

    lines.append("[Aegis] Impact:")
    lines.append(f"[Aegis] - Estimated AI iterations avoided: {signal.estimated_calls_avoided}")
    if impact_estimate.get("activity_detected"):
        low = int(impact_estimate.get("calls_avoided_low", signal.estimated_calls_avoided))
        high = int(impact_estimate.get("calls_avoided_high", signal.estimated_calls_avoided))
        lines.append(f"[Aegis] - Prevented {low}-{high} unnecessary retries")
    else:
        lines.append("[Aegis] - Prevented retries: range unavailable until repeated activity is detected")

    changed_files = signal.details.get("changed_files")
    if not isinstance(changed_files, int):
        changed_files = impact_estimate.get("changed_file_count")
    max_files = control.get("max_files")
    if isinstance(changed_files, int) and isinstance(max_files, int):
        lines.append(f"[Aegis] - Reduced scope from {changed_files} files to {max_files}")

    if escalation in {"medium", "high"}:
        lines.extend(
            [
                "[Aegis] Escalation:",
                "[Aegis] This issue is persisting.",
            ]
        )
        if escalation == "high":
            lines.append("[Aegis] Strong recommendation: STOP current attempt and reset approach.")
        else:
            lines.append("[Aegis] Strong recommendation: pause current attempt and reset approach.")
    if fallback:
        lines.append("[Aegis] Marked as local fallback.")
    return "\n".join(lines)


def _contextual_explanation(signal_type: str) -> str:
    if signal_type == "loop_signal":
        return "No progress detected across multiple iterations"
    if signal_type == "scope_drift_signal":
        return "File changes expanded beyond expected task scope"
    if signal_type == "diff_growth_signal":
        return "Change size increasing rapidly without convergence"
    return "Control needed to stabilize workflow"


def _startup_banner() -> str:
    return "\n".join(
        [
            "[Aegis]",
            "[Aegis] Auto mode active",
            "[Aegis]",
            "[Aegis] Watching for:",
            "[Aegis] - retry loops",
            "[Aegis] - scope drift",
            "[Aegis] - inefficient changes",
            "[Aegis]",
            "[Aegis] Run your AI tool normally. I'll step in if something goes wrong.",
        ]
    )


def _minimal_repeat_message(signal_type: str, escalation: str) -> str:
    issue = _signal_label(signal_type)
    if escalation in {"medium", "high"}:
        return f"[Aegis] {issue} still present - escalation monitoring active."
    return f"[Aegis] {issue} still present - monitoring for escalation."


def _should_emit_signal_output(
    *,
    outcome: DecisionOutcome,
    display_state: dict[str, dict[str, Any]],
    now_ts: float,
) -> tuple[bool, str]:
    issue_state = display_state.setdefault(
        outcome.signal_type,
        {
            "last_output_timestamp": 0.0,
            "last_escalation": "",
            "last_fingerprint": None,
            "repeat_count": 0,
        },
    )

    last_escalation = str(issue_state.get("last_escalation", ""))
    last_fingerprint = issue_state.get("last_fingerprint")
    repeat_count = int(issue_state.get("repeat_count", 0))

    escalation_changed = outcome.escalation != last_escalation
    state_changed = outcome.state_fingerprint != last_fingerprint

    if last_fingerprint is None:
        issue_state.update(
            {
                "last_output_timestamp": now_ts,
                "last_escalation": outcome.escalation,
                "last_fingerprint": outcome.state_fingerprint,
                "repeat_count": 0,
            }
        )
        return True, outcome.full_output

    if escalation_changed or state_changed:
        issue_state.update(
            {
                "last_output_timestamp": now_ts,
                "last_escalation": outcome.escalation,
                "last_fingerprint": outcome.state_fingerprint,
                "repeat_count": 0,
            }
        )
        return True, outcome.full_output

    repeat_count += 1
    issue_state["repeat_count"] = repeat_count

    if outcome.escalation in {"medium", "high"}:
        last_ts = float(issue_state.get("last_output_timestamp", 0.0))
        if (now_ts - last_ts) >= ESCALATION_STATUS_INTERVAL_SECONDS or repeat_count == 1:
            issue_state["last_output_timestamp"] = now_ts
            return True, outcome.minimal_output
        return False, ""

    if repeat_count == 1:
        issue_state["last_output_timestamp"] = now_ts
        return True, outcome.minimal_output
    issue_state["last_output_timestamp"] = now_ts
    return False, ""


def process_signal_candidate(
    *,
    client: AegisClient,
    observation: RepoObservation,
    signal: SignalCandidate,
    previous_snapshot: DiffSnapshot | None,
    session_id: str,
    issue_counts: dict[str, int] | None = None,
    verbose: bool = False,
    cwd: str | Path | None = None,
) -> str:
    return _process_signal_candidate(
        client=client,
        observation=observation,
        signal=signal,
        previous_snapshot=previous_snapshot,
        session_id=session_id,
        issue_counts=issue_counts,
        verbose=verbose,
        cwd=cwd,
    ).full_output


def _process_signal_candidate(
    *,
    client: AegisClient,
    observation: RepoObservation,
    signal: SignalCandidate,
    previous_snapshot: DiffSnapshot | None,
    session_id: str,
    issue_counts: dict[str, int] | None = None,
    verbose: bool = False,
    cwd: str | Path | None = None,
) -> DecisionOutcome:
    payload = _build_signal_payload(
        observation=observation,
        signal=signal,
        previous_snapshot=previous_snapshot,
        session_id=session_id,
    )
    append_auto_event(
        event_type="local_signal",
        details=payload,
        session_id=session_id,
        cwd=cwd,
    )

    same_issue_count = 1
    if issue_counts is not None:
        same_issue_count = int(issue_counts.get(signal.signal_type, 0)) + 1
        issue_counts[signal.signal_type] = same_issue_count

    decision, fallback = _aegis_decision_for_signal(client=client, payload=payload, signal=signal)
    actions = list(decision.get("actions") or [])
    control = _derive_control(actions=actions, signal=signal)
    confidence = _confidence_label(same_issue_count)
    escalation = _escalation_level(same_issue_count)
    calls_low, calls_high = _impact_range(signal.signal_type)
    activity_detected = bool(signal.details.get("activity_detected", False))
    impact_estimate = {
        "calls_avoided_low": calls_low,
        "calls_avoided_high": calls_high,
        "estimated_cost_saved": signal.estimated_cost_saved,
        "activity_detected": activity_detected,
        "changed_file_count": observation.changed_file_count,
    }

    decision_event = {
        **decision,
        "control": control,
        "confidence": confidence,
        "escalation": escalation,
        "impact_estimate": impact_estimate,
        "same_issue_count": same_issue_count,
    }
    append_auto_event(
        event_type="aegis_decision",
        details=decision_event,
        session_id=session_id,
        cwd=cwd,
    )
    control_state = build_control_state(
        session_id=session_id,
        source=str(decision.get("source", "local_fallback")),
        source_event=signal.signal_type,
        fallback=fallback,
        confidence=confidence,
        escalation=escalation,
        control=control,
        human_controls=_control_guidance(control),
        reason=str(decision.get("explanation") or _contextual_explanation(signal.signal_type)),
    )
    write_control_state(control_state, cwd=cwd)

    full_output = _render_decision_output(
        signal=signal,
        decision=decision,
        control=control,
        confidence=confidence,
        escalation=escalation,
        impact_estimate=impact_estimate,
        fallback=fallback,
        show_structured_control=verbose,
    )
    fingerprint = (
        signal.details.get("cycles"),
        signal.details.get("changed_files"),
        signal.details.get("file_growth"),
        signal.details.get("prior_insertions"),
        signal.details.get("current_insertions"),
        escalation,
    )
    return DecisionOutcome(
        full_output=full_output,
        minimal_output=_minimal_repeat_message(signal.signal_type, escalation),
        signal_type=signal.signal_type,
        escalation=escalation,
        confidence=confidence,
        state_fingerprint=fingerprint,
    )


def run_auto_mode(
    *,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    verbose: bool = False,
    background_worker: bool = False,
    cwd: str | Path | None = None,
) -> int:
    preflight = preflight_check(cwd=cwd, print_messages=not background_worker)
    if not preflight.get("can_run"):
        return 1

    startup_state = read_auto_state(cwd=cwd)
    project_path = _resolve_project_path(cwd=cwd, state=startup_state)
    state = read_auto_state(cwd=project_path)
    if state.get("running") and not state.get("stop_requested") and not background_worker:
        print("[Aegis] Auto mode is already running.")
        return 0

    session_id = str(uuid.uuid4())
    now = _utc_now_iso()
    mode = "background" if background_worker else "foreground"
    bounded_interval = max(2.0, min(interval_seconds, 5.0))
    write_auto_state(
        {
            "running": True,
            "stop_requested": False,
            "session_id": session_id,
            "started_at": now,
            "last_heartbeat_at": now,
            "last_session_id": session_id,
            "mode": mode,
            "pid": os.getpid(),
            "interval_seconds": bounded_interval,
            "project_path": str(project_path),
        },
        cwd=project_path,
    )
    append_auto_event(
        event_type="auto_started",
        details={
            "interval_seconds": bounded_interval,
            "mode": mode,
            "project_path": str(project_path),
        },
        session_id=session_id,
        cwd=project_path,
    )
    if not background_worker:
        print(_startup_banner())

    engine = AutoHeuristicEngine()
    client = _build_client()
    no_issues_since = time.time()
    no_issues_notified = False
    issue_counts: dict[str, int] = {}
    display_state: dict[str, dict[str, Any]] = {}
    try:
        while True:
            live_state = read_auto_state(cwd=project_path)
            if live_state.get("stop_requested"):
                break

            heartbeat_time = _utc_now_iso()
            updated_state = dict(live_state)
            updated_state.update(
                {
                    "running": True,
                    "session_id": session_id,
                    "started_at": now,
                    "last_heartbeat_at": heartbeat_time,
                    "last_session_id": session_id,
                    "mode": mode,
                    "pid": os.getpid(),
                    "interval_seconds": bounded_interval,
                    "project_path": str(project_path),
                }
            )
            write_auto_state(updated_state, cwd=project_path)

            try:
                previous = engine.previous_snapshot
                observation = collect_repo_observation(cwd=str(project_path))
                signals = engine.evaluate(observation)
                for signal in signals:
                    outcome = _process_signal_candidate(
                        client=client,
                        observation=observation,
                        signal=signal,
                        previous_snapshot=previous,
                        session_id=session_id,
                        issue_counts=issue_counts,
                        verbose=verbose,
                        cwd=project_path,
                    )
                    emit, output = _should_emit_signal_output(
                        outcome=outcome,
                        display_state=display_state,
                        now_ts=time.time(),
                    )
                    if emit and output:
                        print(output)

                if signals:
                    if verbose:
                        no_issues_notified = False
                        no_issues_since = time.time()
                elif not no_issues_notified and (time.time() - no_issues_since) >= NO_ISSUES_FEEDBACK_SECONDS:
                    print("[Aegis] No issues detected yet - monitoring workflow.")
                    no_issues_notified = True
            except Exception as exc:
                print(f"[Aegis] Temporary auto-mode error: {exc.__class__.__name__}. Continuing monitoring.")

            time.sleep(bounded_interval)
    except KeyboardInterrupt:
        pass
    finally:
        stopped_at = _utc_now_iso()
        write_auto_state(
            {
                "running": False,
                "stop_requested": False,
                "session_id": session_id,
                "started_at": now,
                "last_heartbeat_at": _utc_now_iso(),
                "stopped_at": stopped_at,
                "last_session_id": session_id,
                "mode": mode,
                "pid": os.getpid(),
                "interval_seconds": bounded_interval,
                "project_path": str(project_path),
            },
            cwd=project_path,
        )
        append_auto_event(
            event_type="auto_stopped",
            details={},
            session_id=session_id,
            cwd=project_path,
        )
        if not background_worker:
            print("[Aegis] Auto mode stopped.")
    return 0


def _parse_iso(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _resolve_project_path(*, cwd: str | Path | None, state: dict[str, Any] | None = None) -> Path:
    if state is not None:
        project_path = state.get("project_path")
        if isinstance(project_path, str) and project_path.strip():
            return Path(project_path)
    if cwd is not None:
        return Path(cwd)
    return Path.cwd()


def _heartbeat_deadline_seconds(state: dict[str, Any]) -> float:
    interval = state.get("interval_seconds")
    try:
        interval_value = float(interval)
    except (TypeError, ValueError):
        interval_value = DEFAULT_INTERVAL_SECONDS
    return max(HEARTBEAT_STALE_SECONDS, interval_value * 3.0)


def _heartbeat_age_seconds(*, state: dict[str, Any], now: datetime | None = None) -> float | None:
    heartbeat_raw = state.get("last_heartbeat_at")
    heartbeat_time = _parse_iso(heartbeat_raw)
    if heartbeat_time is None:
        return None
    current_time = now or datetime.now(timezone.utc)
    return max(0.0, (current_time - heartbeat_time).total_seconds())


def _is_heartbeat_stale(*, state: dict[str, Any], now: datetime | None = None) -> bool:
    age = _heartbeat_age_seconds(state=state, now=now)
    if age is None:
        return False
    return age > _heartbeat_deadline_seconds(state)


def _worker_running_status(state: dict[str, Any]) -> str:
    pid = state.get("pid")
    if not state.get("running"):
        return "no"
    if isinstance(pid, int):
        pid_state = _is_pid_running(pid)
        if pid_state is True:
            return "yes"
        if pid_state is False:
            return "no"
        return "unknown"
    return "unknown"


def _worker_health_status(*, state: dict[str, Any], running_status: str) -> str:
    if running_status != "yes":
        if running_status == "no":
            return "no"
        return "unknown"
    age = _heartbeat_age_seconds(state=state)
    if age is None:
        return "unknown"
    if _is_heartbeat_stale(state=state):
        return "no"
    return "yes"


def _monitoring_active(*, state: dict[str, Any]) -> bool:
    running_status = _worker_running_status(state)
    if running_status != "yes":
        return False
    return _worker_health_status(state=state, running_status=running_status) == "yes"


def _duration_minutes(events: list[dict[str, Any]]) -> int:
    if not events:
        return 0
    timestamps: list[datetime] = []
    for event in events:
        parsed = _parse_iso(event.get("timestamp"))
        if parsed is not None:
            timestamps.append(parsed)
    if len(timestamps) < 2:
        return 0
    delta = max(timestamps) - min(timestamps)
    return int(max(0.0, delta.total_seconds()) // 60)


def aggregate_auto_metrics(events: list[dict[str, Any]], *, session_id: str | None = None) -> AutoMetrics:
    scoped = []
    for event in events:
        event_session_id = event.get("session_id")
        if session_id is not None and event_session_id != session_id:
            continue
        if event.get("type") in {
            "auto_started",
            "auto_stopped",
            "auto_session_started",
            "auto_session_stopped",
            "local_signal",
            "aegis_decision",
        }:
            scoped.append(event)

    loop_signals = 0
    scope_drift_signals = 0
    diff_growth_signals = 0
    local_signal_count = 0
    aegis_decision_count = 0
    local_fallback_count = 0
    escalation_count = 0
    estimated_calls_saved = 0

    for event in scoped:
        event_type = str(event.get("type"))
        details = event.get("details") or {}
        if event_type == "local_signal":
            local_signal_count += 1
            signal_type = details.get("signal_type")
            if signal_type == "loop_signal":
                loop_signals += 1
            elif signal_type == "scope_drift_signal":
                scope_drift_signals += 1
            elif signal_type == "diff_growth_signal":
                diff_growth_signals += 1
            if details.get("signal_details", {}).get("activity_detected", details.get("activity_detected")):
                calls = details.get("estimated_calls_avoided", 0)
                try:
                    estimated_calls_saved += int(calls)
                except (TypeError, ValueError):
                    pass
        elif event_type == "aegis_decision":
            aegis_decision_count += 1
            if details.get("source") == "local_fallback":
                local_fallback_count += 1
            if details.get("escalation") in {"medium", "high"}:
                escalation_count += 1

    retries_avoided = loop_signals
    notes: list[str] = []
    if escalation_count:
        notes.append("Use tighter prompts for this workflow.")
    elif scope_drift_signals > 0:
        notes.append("Keep scope boundaries narrow and avoid broad edits.")
    elif diff_growth_signals > 0:
        notes.append("Split changes into smaller checkpoints.")
    elif loop_signals > 0:
        notes.append("Inspect failed steps before retrying.")
    else:
        notes.append("Workflow is stable; keep current controls.")

    session_ids = {
        str(event.get("session_id"))
        for event in scoped
        if event.get("session_id") not in (None, "")
    }
    return AutoMetrics(
        duration_minutes=_duration_minutes(scoped),
        loop_signals=loop_signals,
        scope_drift_signals=scope_drift_signals,
        diff_growth_signals=diff_growth_signals,
        local_signal_count=local_signal_count,
        aegis_decision_count=aegis_decision_count,
        local_fallback_count=local_fallback_count,
        escalation_count=escalation_count,
        retries_avoided=retries_avoided,
        estimated_calls_saved=estimated_calls_saved,
        estimated_cost_saved=round(estimated_calls_saved * CALL_COST_USD, 2),
        notes=notes,
        session_count=max(1, len(session_ids)) if scoped else 0,
    )


def latest_auto_session_id(events: list[dict[str, Any]]) -> str | None:
    auto_events = [
        event
        for event in events
        if isinstance(event.get("session_id"), str)
        and event.get("type")
        in {
            "auto_started",
            "auto_stopped",
            "auto_session_started",
            "auto_session_stopped",
            "local_signal",
            "aegis_decision",
        }
    ]
    if not auto_events:
        return None
    auto_events.sort(key=lambda e: str(e.get("timestamp", "")))
    return str(auto_events[-1].get("session_id"))


def _status_event_label(event: dict[str, Any]) -> str:
    event_type = str(event.get("type", ""))
    details = event.get("details") or {}
    if event_type in {"auto_started", "auto_session_started"}:
        return "Monitoring session started"
    if event_type == "local_signal":
        return _signal_label(str(details.get("signal_type", "")))
    if event_type == "aegis_decision":
        if details.get("source") == "local_fallback":
            return "Local fallback recommendation"
        return "Aegis recommendation issued"
    return event_type or "none"


def _times_label(count: int) -> str:
    suffix = "time" if count == 1 else "times"
    return f"{count} {suffix}"


def _summary_retry_line(metrics: AutoMetrics) -> str:
    if metrics.estimated_calls_saved <= 0:
        return "[Aegis] - Prevented retries: none observed"
    if metrics.loop_signals > 0:
        low = metrics.loop_signals * 2
        high = metrics.loop_signals * 4
        return f"[Aegis] - Prevented {low}-{high} unnecessary retries"
    return f"[Aegis] - Prevented at least {metrics.estimated_calls_saved} unnecessary retries"


def _find_scope_reduction_line(
    events: list[dict[str, Any]],
    *,
    session_id: str | None = None,
) -> str:
    for index in range(len(events) - 1, -1, -1):
        event = events[index]
        if session_id is not None and event.get("session_id") != session_id:
            continue
        if event.get("type") != "aegis_decision":
            continue
        details = event.get("details") or {}
        control = details.get("control") or {}
        suggested = control.get("max_files")
        if not isinstance(suggested, int):
            continue

        changed_files: int | None = None
        for back_index in range(index - 1, -1, -1):
            prior = events[back_index]
            if session_id is not None and prior.get("session_id") != session_id:
                continue
            if prior.get("type") != "local_signal":
                continue
            prior_details = prior.get("details") or {}
            signal_details = prior_details.get("signal_details") or {}
            raw_changed = signal_details.get("changed_files")
            if isinstance(raw_changed, int):
                changed_files = raw_changed
                break
            repo_observation = prior_details.get("repo_observation") or {}
            raw_repo_changed = repo_observation.get("changed_file_count")
            if isinstance(raw_repo_changed, int):
                changed_files = raw_repo_changed
                break
        if isinstance(changed_files, int):
            return f"[Aegis] - Reduced scope from {changed_files} files to {suggested}"
    return "[Aegis] - Scope reduction: no scope-limiting intervention recorded"


def _active_controls_summary_line(*, cwd: str | Path | None = None) -> str:
    state = read_control_state(cwd=cwd)
    if state is None:
        return "[Aegis] - Active controls issued: none"
    if is_control_expired(state):
        return "[Aegis] - Active controls issued: present (expired)"
    return "[Aegis] - Active controls issued: present"


def render_status(*, cwd: str | Path | None = None) -> str:
    state = read_auto_state(cwd=cwd)
    project_path = state.get("project_path") or str(Path(cwd) if cwd is not None else Path.cwd())
    observation = collect_repo_observation(cwd=project_path)
    events = read_all_session_events(cwd=project_path)
    latest_event = None
    for event in reversed(events):
        if event.get("type") in {"local_signal", "aegis_decision", "auto_started", "auto_session_started"}:
            latest_event = event
            break

    project_session_log = session_log_path(cwd=project_path)
    pid = state.get("pid")
    running_status = _worker_running_status(state)
    running_label = running_status
    if running_status == "unknown" and isinstance(pid, int):
        running_label = "unknown (PID recorded, process check unavailable)"
    heartbeat = state.get("last_heartbeat_at")
    heartbeat_label = str(heartbeat) if isinstance(heartbeat, str) and heartbeat else "none"
    worker_health = _worker_health_status(state=state, running_status=running_status)

    mode_label = str(state.get("mode", "unknown"))
    if latest_event is not None and latest_event.get("type") == "aegis_decision":
        details = latest_event.get("details") or {}
        if details.get("source") == "local_fallback":
            mode_label = "local fallback"

    lines = [
        f"[Aegis] Auto mode running: {running_label}",
        f"[Aegis] Mode: {mode_label}",
        f"[Aegis] PID: {pid if isinstance(pid, int) else 'none'}",
        f"[Aegis] Last heartbeat: {heartbeat_label}",
        f"[Aegis] Worker healthy: {worker_health}",
        f"[Aegis] Project path: {project_path}",
        f"[Aegis] Branch: {observation.branch}",
        f"[Aegis] Changed files: {observation.changed_file_count}",
        "[Aegis] Diff summary: "
        f"{observation.diff_summary.get('files_changed', 0)} files changed, "
        f"{observation.diff_summary.get('insertions', 0)} insertions, "
        f"{observation.diff_summary.get('deletions', 0)} deletions",
    ]
    if isinstance(pid, int) and _is_heartbeat_stale(state=state):
        lines.append("[Aegis] Auto mode may not be active. Run aegis start again.")
    elif running_status == "unknown":
        lines.append("[Aegis] Worker status unknown. Run aegis start again to re-establish monitoring.")
    elif worker_health == "unknown":
        lines.append("[Aegis] Worker health unknown. Run aegis start again to re-establish monitoring.")
    if latest_event is None:
        lines.append("[Aegis] Last event: none")
    else:
        lines.append(f"[Aegis] Last event: {_status_event_label(latest_event)}")
    lines.append(f"[Aegis] Session log path: {project_session_log}")
    return "\n".join(lines)


def render_summary(*, cwd: str | Path | None = None) -> str:
    state = read_auto_state(cwd=cwd)
    project_path = state.get("project_path") or str(Path(cwd) if cwd is not None else Path.cwd())
    events = read_all_session_events(cwd=project_path)
    session_id = latest_auto_session_id(events)
    if session_id is None:
        if _monitoring_active(state=state):
            return "[Aegis] Monitoring active. No instability events detected yet."
        return "[Aegis] No active monitoring session found. Run aegis start."

    metrics = aggregate_auto_metrics(events, session_id=session_id)
    if metrics.local_signal_count == 0 and metrics.aegis_decision_count == 0:
        if _monitoring_active(state=state):
            return "[Aegis] Monitoring active. No instability events detected yet."
        return "[Aegis] No active monitoring session found. Run aegis start."

    lines = [
        "[Aegis] Aegis Summary (Session)",
        "",
        f"[Aegis] Duration: {metrics.duration_minutes} min",
        "",
        "[Aegis] Issues caught:",
        f"[Aegis] - Loop detected ({_times_label(metrics.loop_signals)})",
        f"[Aegis] - Scope drift detected ({_times_label(metrics.scope_drift_signals)})",
        f"[Aegis] - Large change detected ({_times_label(metrics.diff_growth_signals)})",
        "",
        "[Aegis] Interventions:",
        f"[Aegis] - Control signals issued: {metrics.aegis_decision_count}",
        f"[Aegis] - Escalations: {metrics.escalation_count}",
        _active_controls_summary_line(cwd=project_path),
        "",
        "[Aegis] Impact:",
        f"[Aegis] - Estimated AI iterations avoided: {metrics.estimated_calls_saved}",
        _summary_retry_line(metrics),
        _find_scope_reduction_line(events, session_id=session_id),
        "",
        "[Aegis] Recommendation:",
        f"[Aegis] {metrics.notes[0]}",
    ]
    return "\n".join(lines)


def render_stats(*, cwd: str | Path | None = None) -> str:
    events = read_all_session_events(cwd=cwd)
    metrics = aggregate_auto_metrics(events)
    if metrics.session_count == 0:
        return "[Aegis] No auto-mode events found yet."

    lines = [
        "[Aegis] Aegis Stats (All Sessions)",
        "",
        f"[Aegis] Sessions: {metrics.session_count}",
        f"[Aegis] Duration: {metrics.duration_minutes} min",
        "",
        "[Aegis] Issues caught:",
        f"[Aegis] - Loop detected ({_times_label(metrics.loop_signals)})",
        f"[Aegis] - Scope drift detected ({_times_label(metrics.scope_drift_signals)})",
        f"[Aegis] - Large change detected ({_times_label(metrics.diff_growth_signals)})",
        "",
        "[Aegis] Interventions:",
        f"[Aegis] - Control signals issued: {metrics.aegis_decision_count}",
        f"[Aegis] - Escalations: {metrics.escalation_count}",
        _active_controls_summary_line(cwd=cwd),
        "",
        "[Aegis] Impact:",
        f"[Aegis] - Estimated AI iterations avoided: {metrics.estimated_calls_saved}",
        _summary_retry_line(metrics),
        _find_scope_reduction_line(events),
    ]
    return "\n".join(lines)
