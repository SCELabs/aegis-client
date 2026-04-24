from __future__ import annotations

from typing import Any

from .observe import RepoObservation


def _format_actions(actions: list[dict[str, Any]]) -> str:
    if not actions:
        return "- none"
    lines = []
    for action in actions:
        action_type = action.get("type", "unknown")
        reason = action.get("reason")
        if reason:
            lines.append(f"- {action_type}: {reason}")
        else:
            lines.append(f"- {action_type}")
    return "\n".join(lines)


def render_diagnose(observation: RepoObservation, result: Any) -> str:
    lines = [
        "Aegis Diagnose",
        f"Repo: {observation.cwd}",
        f"Branch: {observation.branch}",
        f"Dirty: {'yes' if observation.dirty else 'no'}",
        f"Changed files: {observation.changed_file_count}",
        "",
        "Summary:",
        result.summary(),
        "",
        "Actions:",
        _format_actions(getattr(result, "actions", [])),
        "",
        "Explanation:",
        getattr(result, "explanation", None) or "No explanation provided.",
    ]
    return "\n".join(lines)


def render_plan(task: str, observation: RepoObservation, result: Any) -> str:
    lines = [
        "Aegis Plan",
        f"Task: {task}",
        f"Branch: {observation.branch}",
        f"Changed files: {observation.changed_file_count}",
        "",
        "Controlled execution plan:",
        str(getattr(result, "final_answer", None) or getattr(result, "output", None) or "No plan output returned."),
        "",
        "Actions:",
        _format_actions(getattr(result, "actions", [])),
        "",
        "Explanation:",
        getattr(result, "explanation", None) or "No explanation provided.",
    ]
    return "\n".join(lines)


def render_review(*, risk_level: str, recommendation: str, observation: RepoObservation, result: Any) -> str:
    lines = [
        "Aegis Review",
        f"Branch: {observation.branch}",
        f"Changed files: {observation.changed_file_count}",
        f"Scope drift risk: {risk_level}",
        "",
        "Recommended next action:",
        recommendation,
        "",
        "Aegis explanation:",
        getattr(result, "explanation", None) or "No explanation provided.",
    ]
    return "\n".join(lines)
