from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import requests

from aegis import AegisClient

from .auto import (
    render_doctor,
    render_stats,
    render_status,
    render_summary,
    reset_project_runtime,
    run_auto_mode,
    start_auto_mode_background,
    stop_auto_mode,
)
from .attach import run_attach
from .config import DEFAULT_BASE_URL, ENV_BASE_URL, resolve_runtime_config, write_user_config
from .control import clear_control_state, render_control_prompt, render_control_state
from .observe import RepoObservation, collect_repo_observation
from .prompts import prompt_email
from .render import render_diagnose, render_plan, render_review
from .session import append_session_event, read_recent_session_events


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aegis", description="Aegis Shell V1")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize Aegis shell config")
    init_parser.add_argument("--base-url", default=None, help="Aegis backend base URL")
    init_parser.set_defaults(handler=_handle_init)

    diagnose_parser = subparsers.add_parser("diagnose", help="Diagnose repo workflow stability")
    diagnose_parser.set_defaults(handler=_handle_diagnose)

    plan_parser = subparsers.add_parser("plan", help="Generate a controlled execution plan")
    plan_parser.add_argument("task", help="Task to plan")
    plan_parser.set_defaults(handler=_handle_plan)

    review_parser = subparsers.add_parser("review", help="Review scope drift risk")
    review_parser.set_defaults(handler=_handle_review)

    handoff_parser = subparsers.add_parser("handoff", help="Create a markdown handoff file")
    handoff_parser.set_defaults(handler=_handle_handoff)

    auto_parser = subparsers.add_parser("auto", help="Run auto mode observation loop")
    auto_parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Polling interval in seconds (bounded to 2-5s)",
    )
    auto_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show structured control details in auto-mode output",
    )
    auto_parser.add_argument(
        "--background-worker",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    auto_parser.set_defaults(handler=_handle_auto)

    start_parser = subparsers.add_parser("start", help="Start auto mode in the background")
    start_parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Polling interval in seconds (bounded to 2-5s)",
    )
    start_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show structured control details in background worker output",
    )
    start_parser.set_defaults(handler=_handle_start)

    stop_parser = subparsers.add_parser("stop", help="Stop auto mode loop")
    stop_parser.set_defaults(handler=_handle_stop)

    status_parser = subparsers.add_parser("status", help="Show auto mode and repo status")
    status_parser.set_defaults(handler=_handle_status)

    summary_parser = subparsers.add_parser("summary", help="Show current session auto summary")
    summary_parser.set_defaults(handler=_handle_summary)

    stats_parser = subparsers.add_parser("stats", help="Show aggregate auto stats")
    stats_parser.set_defaults(handler=_handle_stats)

    attach_parser = subparsers.add_parser("attach", help="Attach Aegis to an existing pipeline command")
    attach_parser.add_argument("--cmd", required=True, help="Command to run under Aegis observation")
    attach_parser.add_argument(
        "--simulate",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run in simulation mode (default: true)",
    )
    attach_parser.add_argument("--log", default=None, help="Optional log file path to read during/after run")
    attach_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON report")
    attach_parser.add_argument("--report", default=None, help="Write rendered attach report to this path")
    attach_parser.add_argument("--no-live", action="store_true", help="Suppress live command output")
    attach_parser.add_argument(
        "--interval",
        type=float,
        default=3.0,
        help="Observation polling interval in seconds (bounded to 2-5s)",
    )
    attach_parser.set_defaults(handler=_handle_attach)

    control_parser = subparsers.add_parser("control", help="Inspect or manage active control state")
    control_parser.add_argument(
        "control_action",
        nargs="?",
        choices=["clear", "apply-prompt"],
        help="Clear control state or render a pasteable prompt block",
    )
    control_parser.add_argument(
        "--json",
        action="store_true",
        help="Show control state as raw JSON",
    )
    control_parser.set_defaults(handler=_handle_control)

    doctor_parser = subparsers.add_parser("doctor", help="Show shell diagnostics")
    doctor_parser.set_defaults(handler=_handle_doctor)

    reset_parser = subparsers.add_parser("reset", help="Reset project runtime state")
    reset_parser.set_defaults(handler=_handle_reset)

    return parser


def _resolve_init_base_url(cli_base_url: str | None) -> str:
    if cli_base_url:
        return cli_base_url.rstrip("/")
    runtime = resolve_runtime_config()
    return str(runtime.get("base_url") or DEFAULT_BASE_URL).rstrip("/")


def _build_client() -> AegisClient:
    runtime = resolve_runtime_config()
    return AegisClient(
        api_key=runtime.get("api_key"),
        base_url=runtime.get("base_url"),
    )


def _risk_from_observation(observation: RepoObservation) -> tuple[str, str]:
    files_changed = observation.diff_summary.get("files_changed", 0)
    changed_file_count = observation.changed_file_count

    if changed_file_count >= 15 or files_changed >= 15:
        return "high", "Create a checkpoint commit and split the work into smaller reviewable steps."
    if changed_file_count >= 5 or files_changed >= 5:
        return "medium", "Run targeted tests and lock the task boundary before continuing."
    return "low", "Proceed with implementation and keep changes scoped to the current task."


def _print(text: Any) -> None:
    print(text)


def _handle_init(args: argparse.Namespace) -> int:
    base_url = _resolve_init_base_url(args.base_url)
    email = prompt_email()

    response = requests.post(
        f"{base_url}/v1/onboard",
        json={"email": email},
        headers={"Content-Type": "application/json"},
        timeout=30.0,
    )
    if not response.ok:
        raise SystemExit(f"Onboard failed ({response.status_code}): {response.text}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise SystemExit("Onboard failed: invalid JSON response.") from exc

    api_key = payload.get("api_key")
    if not api_key:
        raise SystemExit("Onboard failed: missing api_key in response.")

    path = write_user_config(api_key=api_key, base_url=base_url)
    _print(f"Initialized Aegis shell config at {path}")
    _print(f"Environment overrides supported: {ENV_BASE_URL}, AEGIS_API_KEY")
    return 0


def _handle_diagnose(_: argparse.Namespace) -> int:
    observation = collect_repo_observation()
    client = _build_client()

    symptoms = ["unstable_workflow"] if observation.dirty else ["stable_workflow"]
    severity = "medium" if observation.dirty else "low"
    step_input = observation.to_dict()

    result = client.auto().step(
        step_name="dev_repo_diagnosis",
        step_input=step_input,
        symptoms=symptoms,
        severity=severity,
    )

    append_session_event(command="diagnose", observation=observation, result=result)
    _print(render_diagnose(observation, result))
    return 0


def _handle_plan(args: argparse.Namespace) -> int:
    observation = collect_repo_observation()
    client = _build_client()

    step_input = {
        "task": args.task,
        "repo_observation": observation.to_dict(),
    }
    result = client.auto().step(
        step_name="dev_task_plan",
        step_input=step_input,
        symptoms=["unstable_workflow"] if observation.dirty else ["stable_workflow"],
        severity="medium" if observation.dirty else "low",
    )

    append_session_event(
        command="plan",
        observation=observation,
        result=result,
        task=args.task,
    )
    _print(render_plan(args.task, observation, result))
    return 0


def _handle_review(_: argparse.Namespace) -> int:
    observation = collect_repo_observation()
    risk_level, recommendation = _risk_from_observation(observation)
    client = _build_client()

    messages = [
        {
            "role": "user",
            "content": json.dumps(
                {
                    "observation": observation.to_dict(),
                    "scope_drift_signals": {
                        "changed_file_count": observation.changed_file_count,
                        "diff_summary": observation.diff_summary,
                    },
                }
            ),
        }
    ]
    result = client.auto().context(
        objective="Assess repository scope drift risk and recommend the next action.",
        messages=messages,
        severity="medium" if risk_level != "low" else "low",
    )

    append_session_event(command="review", observation=observation, result=result)
    _print(
        render_review(
            risk_level=risk_level,
            recommendation=recommendation,
            observation=observation,
            result=result,
        )
    )
    return 0


def _build_handoff_markdown(
    *,
    observation: RepoObservation,
    recent_events: list[dict[str, Any]],
) -> str:
    inferred_task = None
    for event in reversed(recent_events):
        task = event.get("task")
        if isinstance(task, str) and task.strip():
            inferred_task = task.strip()
            break

    recent_action_lines = []
    for event in recent_events[-8:]:
        command = str(event.get("command", "unknown"))
        timestamp = str(event.get("timestamp", "unknown_time"))
        debug = event.get("result_debug_summary")
        if debug:
            recent_action_lines.append(f"- {timestamp} `{command}` -> {debug}")
        else:
            recent_action_lines.append(f"- {timestamp} `{command}`")

    markdown_lines = [
        "# Aegis Handoff",
        "",
        f"- Branch: `{observation.branch}`",
        f"- Working directory: `{observation.cwd}`",
        f"- Dirty repo: `{'yes' if observation.dirty else 'no'}`",
        f"- Changed files: `{observation.changed_file_count}`",
        "",
    ]
    if inferred_task:
        markdown_lines.append(f"- Task: {inferred_task}")
        markdown_lines.append("")

    markdown_lines.extend(
        [
            "## Git Status",
            "```",
            observation.status_short or "(clean)",
            "```",
            "",
            "## Git Diff Stat",
            "```",
            observation.diff_stat or "(no diff)",
            "```",
            "",
            "## Recent Session Actions",
        ]
    )
    if recent_action_lines:
        markdown_lines.extend(recent_action_lines)
    else:
        markdown_lines.append("- none")
    markdown_lines.append("")
    return "\n".join(markdown_lines)


def _handle_handoff(_: argparse.Namespace) -> int:
    observation = collect_repo_observation()
    recent_events = read_recent_session_events(limit=20)
    markdown = _build_handoff_markdown(observation=observation, recent_events=recent_events)

    handoff_path = Path.cwd() / ".aegis" / "handoff.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    handoff_path.write_text(markdown, encoding="utf-8")

    append_session_event(command="handoff", observation=observation, result=None)
    _print(markdown)
    _print(f"Saved handoff to {handoff_path}")
    return 0


def _handle_auto(args: argparse.Namespace) -> int:
    interval = max(2.0, min(float(args.interval), 5.0))
    return run_auto_mode(
        interval_seconds=interval,
        verbose=bool(args.verbose),
        background_worker=bool(args.background_worker),
    )


def _handle_start(args: argparse.Namespace) -> int:
    interval = max(2.0, min(float(args.interval), 5.0))
    return start_auto_mode_background(interval_seconds=interval, verbose=bool(args.verbose))


def _handle_stop(_: argparse.Namespace) -> int:
    stopped = stop_auto_mode()
    if stopped:
        _print("[Aegis] Stop signal sent. Auto mode will stop shortly.")
    else:
        _print("[Aegis] Auto mode is not running.")
    return 0


def _handle_status(_: argparse.Namespace) -> int:
    _print(render_status())
    return 0


def _handle_summary(_: argparse.Namespace) -> int:
    _print(render_summary())
    return 0


def _handle_stats(_: argparse.Namespace) -> int:
    _print(render_stats())
    return 0


def _handle_attach(args: argparse.Namespace) -> int:
    interval = max(2.0, min(float(args.interval), 5.0))
    rc, output = run_attach(
        command=str(args.cmd),
        simulate=bool(args.simulate),
        log_path=args.log,
        as_json=bool(args.json),
        live_output=not bool(args.no_live),
        interval_seconds=interval,
    )
    _print(output)
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(str(output), encoding="utf-8")
        _print(f"[Aegis] Report saved to: {report_path}")
    return rc


def _handle_control(args: argparse.Namespace) -> int:
    action = getattr(args, "control_action", None)
    if action == "clear":
        cleared = clear_control_state()
        if cleared:
            _print("[Aegis] Cleared active control state.")
        else:
            _print("[Aegis] No active control state found.")
        return 0
    if action == "apply-prompt":
        _print(render_control_prompt())
        return 0

    _print(render_control_state(as_json=bool(getattr(args, "json", False))))
    return 0


def _handle_doctor(_: argparse.Namespace) -> int:
    _print(render_doctor())
    return 0


def _handle_reset(_: argparse.Namespace) -> int:
    _print(reset_project_runtime())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
