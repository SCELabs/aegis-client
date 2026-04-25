from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class RepoObservation:
    cwd: str
    branch: str
    status_short: str
    diff_stat: str
    changed_file_count: int
    dirty: bool
    diff_summary: dict[str, int]

    def to_dict(self) -> dict:
        return {
            "cwd": self.cwd,
            "branch": self.branch,
            "status_short": self.status_short,
            "diff_stat": self.diff_stat,
            "changed_file_count": self.changed_file_count,
            "dirty": self.dirty,
            "diff_summary": self.diff_summary,
        }

    def summary_line(self) -> str:
        return (
            f"branch={self.branch} dirty={self.dirty} "
            f"changed_files={self.changed_file_count}"
        )


def parse_diff_stat(diff_stat: str) -> dict[str, int]:
    files_changed = 0
    insertions = 0
    deletions = 0
    summary_line = ""
    for line in diff_stat.splitlines():
        if line.strip():
            summary_line = line.strip()

    if summary_line:
        files_match = re.search(r"(\d+)\s+files?\s+changed", summary_line)
        insertions_match = re.search(r"(\d+)\s+insertions?\(\+\)", summary_line)
        deletions_match = re.search(r"(\d+)\s+deletions?\(-\)", summary_line)

        if files_match:
            files_changed = int(files_match.group(1))
        if insertions_match:
            insertions = int(insertions_match.group(1))
        if deletions_match:
            deletions = int(deletions_match.group(1))

    return {
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
    }


def _git_output(
    args: list[str],
    *,
    cwd: str,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> str:
    proc = runner(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return (proc.stdout or "").rstrip()


def _normalize_path(value: str) -> str:
    return value.strip().strip('"').replace("\\", "/")


def _is_ignored_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized == ".aegis" or normalized.startswith(".aegis/")


def _extract_status_path(status_line: str) -> str:
    if len(status_line) <= 3:
        return ""
    path_part = status_line[3:].strip()
    if " -> " in path_part:
        path_part = path_part.split(" -> ", 1)[1].strip()
    return path_part


def _parse_numstat_summary(numstat_text: str) -> dict[str, int]:
    files_changed = 0
    insertions = 0
    deletions = 0

    for line in numstat_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split("\t")
        if len(parts) < 3:
            continue
        ins_raw, del_raw, path = parts[0], parts[1], parts[2]
        if _is_ignored_path(path):
            continue
        files_changed += 1
        if ins_raw.isdigit():
            insertions += int(ins_raw)
        if del_raw.isdigit():
            deletions += int(del_raw)

    return {
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
    }


def collect_repo_observation(
    *, cwd: str | None = None, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run
) -> RepoObservation:
    repo_cwd = cwd or os.getcwd()
    branch = _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_cwd, runner=runner) or "unknown"
    status_short = _git_output(["git", "status", "--short"], cwd=repo_cwd, runner=runner)
    diff_stat = _git_output(["git", "diff", "--stat"], cwd=repo_cwd, runner=runner)
    diff_numstat = _git_output(["git", "diff", "--numstat"], cwd=repo_cwd, runner=runner)

    status_lines = []
    for line in status_short.splitlines():
        if not line.strip():
            continue
        path = _extract_status_path(line)
        if _is_ignored_path(path):
            continue
        status_lines.append(line)
    filtered_status_short = "\n".join(status_lines)
    changed_file_count = len(status_lines)
    dirty = changed_file_count > 0
    diff_summary = _parse_numstat_summary(diff_numstat)
    if diff_summary["files_changed"] == 0 and diff_numstat.strip() == "":
        diff_summary = parse_diff_stat(diff_stat)

    return RepoObservation(
        cwd=repo_cwd,
        branch=branch,
        status_short=filtered_status_short,
        diff_stat=diff_stat,
        changed_file_count=changed_file_count,
        dirty=dirty,
        diff_summary=diff_summary,
    )
