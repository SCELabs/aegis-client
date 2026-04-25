from __future__ import annotations

import json
import queue
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .auto import (
    DEFAULT_INTERVAL_SECONDS,
    SignalCandidate,
    _build_client,
    _process_signal_candidate,
    _resolve_project_path,
    read_auto_state,
)
from .observe import RepoObservation, collect_repo_observation
from .session import append_auto_event, read_all_session_events, session_log_path

RETRY_TERMS = ("retry", "retrying", "replan")
VALIDATION_TERMS = ("validation failed", "parse error", "json parse", "schema error", "tool call failed")
RATE_LIMIT_TERMS = ("rate limit", "429")
CONTEXT_TERMS = ("token limit", "context length", "too many tokens")
RETRIEVAL_TERMS = ("retrieval", "retrieved", "rag", "vector search", "no relevant context", "contradiction")
FAILURE_TERMS = ("failed", "failure", "error")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class AttachRunObservation:
    session_id: str
    command: str
    started_at: str
    ended_at: str
    duration_seconds: float
    exit_code: int
    stdout_line_count: int
    stderr_line_count: int
    repeated_line_count: int
    retry_pattern_count: int
    validation_failure_count: int
    rate_limit_signal_count: int
    context_bloat_signal_count: int
    retrieval_signal_count: int
    stall_signal_count: int
    initial_repo_snapshot: dict[str, Any]
    final_repo_snapshot: dict[str, Any]
    diff_growth: int
    changed_file_growth: int
    log_line_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "command": self.command,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
            "stdout_line_count": self.stdout_line_count,
            "stderr_line_count": self.stderr_line_count,
            "repeated_line_count": self.repeated_line_count,
            "retry_pattern_count": self.retry_pattern_count,
            "validation_failure_count": self.validation_failure_count,
            "rate_limit_signal_count": self.rate_limit_signal_count,
            "context_bloat_signal_count": self.context_bloat_signal_count,
            "retrieval_signal_count": self.retrieval_signal_count,
            "stall_signal_count": self.stall_signal_count,
            "initial_repo_snapshot": self.initial_repo_snapshot,
            "final_repo_snapshot": self.final_repo_snapshot,
            "diff_growth": self.diff_growth,
            "changed_file_growth": self.changed_file_growth,
            "log_line_count": self.log_line_count,
        }


@dataclass(slots=True)
class AttachSignal:
    signal_type: str
    severity_candidate: str
    message: str
    details: dict[str, Any]
    estimated_iterations_avoided: int

    def to_signal_candidate(self) -> SignalCandidate:
        return SignalCandidate(
            signal_type=self.signal_type,
            severity_candidate=self.severity_candidate,
            message=self.message,
            local_suggestion="Pause and stabilize the run before continuing.",
            estimated_calls_avoided=self.estimated_iterations_avoided,
            details=self.details,
        )


@dataclass(slots=True)
class AttachReport:
    observation: AttachRunObservation
    controls: list[str]
    projected_impact: dict[str, Any]
    recommended_integration_points: list[str]
    control_state_path: str
    session_log_path: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed": self.observation.to_dict(),
            "controls": self.controls,
            "projected_impact": self.projected_impact,
            "recommended_integration_points": self.recommended_integration_points,
            "control_state_path": self.control_state_path,
            "session_log_path": self.session_log_path,
        }


def _stream_reader(stream: Any, stream_name: str, sink: queue.Queue[tuple[str, str]]) -> None:
    try:
        for raw in iter(stream.readline, ""):
            sink.put((stream_name, raw.rstrip("\n")))
    finally:
        stream.close()


def _lower_contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def _collect_line_metrics(lines: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    retry = 0
    validation = 0
    rate_limit = 0
    context = 0
    retrieval = 0
    failures = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        key = stripped.lower()
        counts[key] = counts.get(key, 0) + 1
        if _lower_contains_any(stripped, RETRY_TERMS):
            retry += 1
        if _lower_contains_any(stripped, VALIDATION_TERMS):
            validation += 1
        if _lower_contains_any(stripped, RATE_LIMIT_TERMS):
            rate_limit += 1
        if _lower_contains_any(stripped, CONTEXT_TERMS):
            context += 1
        if _lower_contains_any(stripped, RETRIEVAL_TERMS):
            retrieval += 1
        if _lower_contains_any(stripped, FAILURE_TERMS):
            failures += 1
    repeated = sum(max(0, count - 1) for count in counts.values() if count > 1)
    return {
        "repeated_line_count": repeated,
        "retry_pattern_count": retry,
        "validation_failure_count": validation,
        "rate_limit_signal_count": rate_limit,
        "context_bloat_signal_count": context,
        "retrieval_signal_count": retrieval,
        "failure_pattern_count": failures,
    }


def _read_log_lines(log_path: str | Path | None) -> list[str]:
    if log_path is None:
        return []
    path = Path(log_path)
    if not path.exists() or not path.is_file():
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []


def _build_attach_signals(observation: AttachRunObservation) -> list[AttachSignal]:
    signals: list[AttachSignal] = []
    if observation.retry_pattern_count >= 2 or observation.repeated_line_count >= 3:
        signals.append(
            AttachSignal(
                signal_type="loop_signal",
                severity_candidate="high" if observation.retry_pattern_count >= 4 else "medium",
                message="Retry/loop behavior observed in pipeline output",
                details={
                    "retry_pattern_count": observation.retry_pattern_count,
                    "repeated_line_count": observation.repeated_line_count,
                    "activity_detected": True,
                },
                estimated_iterations_avoided=max(3, min(12, observation.retry_pattern_count + observation.repeated_line_count)),
            )
        )
    if observation.changed_file_growth >= 3 or observation.diff_growth >= 3:
        signals.append(
            AttachSignal(
                signal_type="scope_drift_signal",
                severity_candidate="high" if observation.changed_file_growth >= 6 else "medium",
                message="Scope drift observed while attached command was running",
                details={
                    "changed_files": observation.final_repo_snapshot.get("changed_file_count", 0),
                    "file_growth": observation.changed_file_growth,
                    "activity_detected": True,
                },
                estimated_iterations_avoided=max(4, observation.changed_file_growth + 2),
            )
        )
    if (
        observation.validation_failure_count > 0
        or observation.context_bloat_signal_count > 0
        or observation.rate_limit_signal_count > 0
        or observation.exit_code != 0
    ):
        signals.append(
            AttachSignal(
                signal_type="diff_growth_signal",
                severity_candidate="high" if observation.exit_code != 0 else "medium",
                message="Execution instability observed (validation/context/rate-limit/failure)",
                details={
                    "validation_failure_count": observation.validation_failure_count,
                    "context_bloat_signal_count": observation.context_bloat_signal_count,
                    "rate_limit_signal_count": observation.rate_limit_signal_count,
                    "exit_code": observation.exit_code,
                    "activity_detected": True,
                },
                estimated_iterations_avoided=max(
                    2,
                    observation.validation_failure_count
                    + observation.context_bloat_signal_count
                    + observation.rate_limit_signal_count
                    + (2 if observation.exit_code != 0 else 0),
                ),
            )
        )
    return signals


def _recommended_integration_points(observation: AttachRunObservation) -> list[str]:
    points: list[str] = []
    if observation.retry_pattern_count > 0 or observation.repeated_line_count > 0:
        points.append("Before retry loop")
    if observation.retrieval_signal_count > 0 or observation.context_bloat_signal_count > 0:
        points.append("After retrieval/context construction")
    if observation.validation_failure_count > 0 or observation.exit_code != 0:
        points.append("Before agent step continuation")
    if not points:
        points.append("Before agent step continuation")
    deduped: list[str] = []
    for point in points:
        if point not in deduped:
            deduped.append(point)
    return deduped


def _render_report(report: AttachReport) -> str:
    obs = report.observation
    controls = report.controls or ["No control actions were generated."]
    lines = [
        "[Aegis] Pipeline Simulation Report",
        "",
        "[Aegis] Observed:",
        f"[Aegis] - Runtime: {int(obs.duration_seconds)} sec",
        f"[Aegis] - Exit status: {obs.exit_code}",
        f"[Aegis] - Repeated retry patterns: {obs.retry_pattern_count}",
        f"[Aegis] - Scope drift: {obs.initial_repo_snapshot.get('changed_file_count', 0)} -> {obs.final_repo_snapshot.get('changed_file_count', 0)} files",
        f"[Aegis] - Validation failures observed: {obs.validation_failure_count}",
        "",
        "[Aegis] Aegis would have:",
    ]
    for control in controls:
        lines.append(f"[Aegis] - {control}")

    projected = report.projected_impact
    lines.extend(
        [
            "",
            "[Aegis] Projected impact:",
            f"[Aegis] - Estimated AI iterations avoided: {projected.get('estimated_ai_iterations_avoided', '0')}",
            f"[Aegis] - Retry loops prevented: {projected.get('retry_loops_prevented', 0)}",
            f"[Aegis] - Scope reduced from {projected.get('scope_from', 0)} files to {projected.get('scope_to', 0)}",
            "",
            "[Aegis] Recommended integration points:",
        ]
    )
    for point in report.recommended_integration_points:
        lines.append(f"[Aegis] - {point}")
    lines.extend(
        [
            "",
            f"[Aegis] Active control state: {report.control_state_path}",
            f"[Aegis] Session log: {report.session_log_path}",
        ]
    )
    return "\n".join(lines)


def run_attach(
    *,
    command: str,
    simulate: bool = True,
    log_path: str | Path | None = None,
    as_json: bool = False,
    live_output: bool = True,
    interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    cwd: str | Path | None = None,
) -> tuple[int, str]:
    project_path = _resolve_project_path(cwd=cwd, state=read_auto_state(cwd=cwd))
    runtime = project_path / ".aegis"
    runtime.mkdir(parents=True, exist_ok=True)

    session_id = str(uuid.uuid4())
    started = time.time()
    started_iso = _utc_now_iso()
    initial_observation = collect_repo_observation(cwd=str(project_path))
    append_auto_event(
        event_type="attach_started",
        details={"command": command, "simulate": bool(simulate), "log_path": str(log_path) if log_path else None},
        session_id=session_id,
        cwd=project_path,
    )

    command_queue: queue.Queue[tuple[str, str]] = queue.Queue()
    proc = subprocess.Popen(
        command,
        cwd=str(project_path),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    assert proc.stdout is not None
    assert proc.stderr is not None
    stdout_thread = threading.Thread(target=_stream_reader, args=(proc.stdout, "stdout", command_queue), daemon=True)
    stderr_thread = threading.Thread(target=_stream_reader, args=(proc.stderr, "stderr", command_queue), daemon=True)
    stdout_thread.start()
    stderr_thread.start()

    bounded_interval = max(2.0, min(float(interval_seconds), 5.0))
    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    last_progress_ts = time.time()
    stall_signal_count = 0
    max_changed_files_seen = initial_observation.changed_file_count
    max_diff_files_seen = int(initial_observation.diff_summary.get("files_changed", 0))

    while proc.poll() is None or not command_queue.empty():
        try:
            stream_name, line = command_queue.get(timeout=0.2)
            if stream_name == "stdout":
                stdout_lines.append(line)
                if live_output:
                    print(line)
            else:
                stderr_lines.append(line)
                if live_output:
                    print(line)
            last_progress_ts = time.time()
        except queue.Empty:
            pass

        if (time.time() - last_progress_ts) >= bounded_interval * 3:
            stall_signal_count += 1
            last_progress_ts = time.time()

        current_obs = collect_repo_observation(cwd=str(project_path))
        max_changed_files_seen = max(max_changed_files_seen, current_obs.changed_file_count)
        max_diff_files_seen = max(max_diff_files_seen, int(current_obs.diff_summary.get("files_changed", 0)))

    stdout_thread.join(timeout=1.0)
    stderr_thread.join(timeout=1.0)
    while not command_queue.empty():
        stream_name, line = command_queue.get()
        if stream_name == "stdout":
            stdout_lines.append(line)
            if live_output:
                print(line)
        else:
            stderr_lines.append(line)
            if live_output:
                print(line)
    exit_code = int(proc.returncode or 0)
    ended = time.time()
    ended_iso = _utc_now_iso()

    log_lines = _read_log_lines(log_path)
    combined_lines = stdout_lines + stderr_lines + log_lines
    metrics = _collect_line_metrics(combined_lines)
    final_observation = collect_repo_observation(cwd=str(project_path))
    changed_growth = max(0, max_changed_files_seen - initial_observation.changed_file_count)
    diff_growth = max(0, max_diff_files_seen - int(initial_observation.diff_summary.get("files_changed", 0)))

    run_observation = AttachRunObservation(
        session_id=session_id,
        command=command,
        started_at=started_iso,
        ended_at=ended_iso,
        duration_seconds=round(max(0.0, ended - started), 2),
        exit_code=exit_code,
        stdout_line_count=len(stdout_lines),
        stderr_line_count=len(stderr_lines),
        repeated_line_count=metrics["repeated_line_count"],
        retry_pattern_count=metrics["retry_pattern_count"],
        validation_failure_count=metrics["validation_failure_count"],
        rate_limit_signal_count=metrics["rate_limit_signal_count"],
        context_bloat_signal_count=metrics["context_bloat_signal_count"],
        retrieval_signal_count=metrics["retrieval_signal_count"],
        stall_signal_count=stall_signal_count,
        initial_repo_snapshot=initial_observation.to_dict(),
        final_repo_snapshot=final_observation.to_dict(),
        diff_growth=diff_growth,
        changed_file_growth=changed_growth,
        log_line_count=len(log_lines),
    )

    append_auto_event(
        event_type="attach_observed",
        details=run_observation.to_dict(),
        session_id=session_id,
        cwd=project_path,
    )

    controls: list[str] = []
    projected_low = 0
    projected_high = 0
    retry_loops_prevented = 0
    issue_counts: dict[str, int] = {}
    if simulate:
        client = _build_client()
        attach_signals = _build_attach_signals(run_observation)
        retry_loops_prevented = sum(1 for sig in attach_signals if sig.signal_type == "loop_signal")
        for attach_signal in attach_signals:
            projected_low += max(1, attach_signal.estimated_iterations_avoided - 1)
            projected_high += attach_signal.estimated_iterations_avoided + 1
            outcome = _process_signal_candidate(
                client=client,
                observation=final_observation,
                signal=attach_signal.to_signal_candidate(),
                previous_snapshot=None,
                session_id=session_id,
                issue_counts=issue_counts,
                verbose=False,
                cwd=project_path,
            )
            for line in outcome.full_output.splitlines():
                if line.startswith("[Aegis] - ") and line not in controls:
                    controls.append(line.replace("[Aegis] - ", "", 1))
            if live_output:
                print(outcome.full_output)

    projected_text = "0"
    if projected_high > 0:
        projected_text = f"{projected_low}-{projected_high}"
    report = AttachReport(
        observation=run_observation,
        controls=controls[:6],
        projected_impact={
            "estimated_ai_iterations_avoided": projected_text,
            "retry_loops_prevented": retry_loops_prevented,
            "scope_from": final_observation.changed_file_count,
            "scope_to": 3 if final_observation.changed_file_count > 3 else final_observation.changed_file_count,
        },
        recommended_integration_points=_recommended_integration_points(run_observation),
        control_state_path=str(project_path / ".aegis" / "control.json"),
        session_log_path=str(session_log_path(cwd=project_path)),
    )

    append_auto_event(
        event_type="attach_completed",
        details={
            "exit_code": exit_code,
            "report": report.to_dict(),
        },
        session_id=session_id,
        cwd=project_path,
    )

    if as_json:
        return 0, json.dumps(report.to_dict(), indent=2, sort_keys=True)
    return 0, _render_report(report)
