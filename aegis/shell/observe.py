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
    return (proc.stdout or "").strip()


def collect_repo_observation(
    *, cwd: str | None = None, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run
) -> RepoObservation:
    repo_cwd = cwd or os.getcwd()
    branch = _git_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_cwd, runner=runner) or "unknown"
    status_short = _git_output(["git", "status", "--short"], cwd=repo_cwd, runner=runner)
    diff_stat = _git_output(["git", "diff", "--stat"], cwd=repo_cwd, runner=runner)

    status_lines = [line for line in status_short.splitlines() if line.strip()]
    changed_file_count = len(status_lines)
    dirty = changed_file_count > 0
    diff_summary = parse_diff_stat(diff_stat)

    return RepoObservation(
        cwd=repo_cwd,
        branch=branch,
        status_short=status_short,
        diff_stat=diff_stat,
        changed_file_count=changed_file_count,
        dirty=dirty,
        diff_summary=diff_summary,
    )
