import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock

from aegis.shell.auto import AutoHeuristicEngine, _process_signal_candidate, render_stats, render_summary
from aegis.shell.cli import main
from aegis.shell.control import (
    build_control_state,
    clear_control_state,
    control_state_path,
    read_control_state,
    render_control_prompt,
    render_control_state,
    write_control_state,
)
from aegis.shell.observe import RepoObservation


def _observation(*, changed_files: int, files_changed: int, insertions: int, deletions: int = 0) -> RepoObservation:
    return RepoObservation(
        cwd="C:/repo",
        branch="feature/control",
        status_short=" M app.py",
        diff_stat=f"{files_changed} files changed, {insertions} insertions(+), {deletions} deletions(-)",
        changed_file_count=changed_files,
        dirty=changed_files > 0,
        diff_summary={
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
        },
    )


class TestControlStateSidecar(unittest.TestCase):
    def test_control_file_written_on_aegis_decision(self):
        engine = AutoHeuristicEngine()
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        signal = engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))[0]

        fake_result = Mock()
        fake_result.actions = [{"type": "increase_coordination_constraints"}]
        fake_result.explanation = "scope tightening"
        fake_result.trace = []
        fake_result.metrics = {}
        fake_result.scope_data = {}
        client = Mock()
        client.auto.return_value.step.return_value = fake_result

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            _process_signal_candidate(
                client=client,
                observation=_observation(changed_files=4, files_changed=4, insertions=6),
                signal=signal,
                previous_snapshot=engine.previous_snapshot,
                session_id="sess-ctrl",
                issue_counts={},
                cwd=cwd,
            )
            state = read_control_state(cwd=cwd)

        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state["source"], "aegis_api")
        self.assertFalse(state["fallback"])
        self.assertEqual(state["source_event"], "loop_signal")
        self.assertIn("human_controls", state)
        self.assertEqual(state["controls"]["validation_required"], state["controls"]["require_validation"])

    def test_control_file_written_on_fallback_decision(self):
        engine = AutoHeuristicEngine()
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        signal = engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))[0]

        client = Mock()
        client.auto.return_value.step.side_effect = RuntimeError("down")

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            _process_signal_candidate(
                client=client,
                observation=_observation(changed_files=2, files_changed=2, insertions=4),
                signal=signal,
                previous_snapshot=engine.previous_snapshot,
                session_id="sess-fallback",
                issue_counts={},
                cwd=cwd,
            )
            state = read_control_state(cwd=cwd)

        self.assertIsNotNone(state)
        assert state is not None
        self.assertEqual(state["source"], "local_fallback")
        self.assertTrue(state["fallback"])

    def test_repeated_decisions_update_confidence_and_escalation(self):
        engine = AutoHeuristicEngine()
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        signal = engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))[0]

        fake_result = Mock()
        fake_result.actions = []
        fake_result.explanation = "control"
        fake_result.trace = []
        fake_result.metrics = {}
        fake_result.scope_data = {}
        client = Mock()
        client.auto.return_value.step.return_value = fake_result
        issue_counts = {"loop_signal": 1}

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            _process_signal_candidate(
                client=client,
                observation=_observation(changed_files=2, files_changed=2, insertions=4),
                signal=signal,
                previous_snapshot=engine.previous_snapshot,
                session_id="sess-escalate",
                issue_counts=issue_counts,
                cwd=cwd,
            )
            first = read_control_state(cwd=cwd)
            _process_signal_candidate(
                client=client,
                observation=_observation(changed_files=2, files_changed=2, insertions=4),
                signal=signal,
                previous_snapshot=engine.previous_snapshot,
                session_id="sess-escalate",
                issue_counts=issue_counts,
                cwd=cwd,
            )
            second = read_control_state(cwd=cwd)

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        assert first is not None and second is not None
        self.assertEqual(first["escalation"], "medium")
        self.assertEqual(first["confidence"], "high")
        self.assertEqual(second["escalation"], "high")
        self.assertEqual(second["confidence"], "high")

    def test_render_control_state_and_prompt_and_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            state = build_control_state(
                session_id="sess-ui",
                source="aegis_api",
                source_event="scope_drift_signal",
                fallback=False,
                confidence="high",
                escalation="medium",
                control={"retry_limit": 1, "max_files": 3, "allow_refactor": False, "require_validation": True},
                human_controls=[
                    "Stop retries",
                    "Limit changes to 2-3 files",
                    "Avoid refactoring unrelated code",
                    "Validate changes before next step",
                ],
                reason="scope drift",
            )
            write_control_state(state, cwd=cwd)

            rendered = render_control_state(cwd=cwd)
            rendered_json = render_control_state(cwd=cwd, as_json=True)
            prompt = render_control_prompt(cwd=cwd)
            cleared = clear_control_state(cwd=cwd)

        self.assertIn("Active Controls", rendered)
        self.assertIn("Source: Aegis API", rendered)
        self.assertIn("Limit changes to 2-3 files", rendered)
        parsed = json.loads(rendered_json)
        self.assertEqual(parsed["session_id"], "sess-ui")
        self.assertIn("Aegis active control state:", prompt)
        self.assertIn("Do not expand scope unless explicitly instructed.", prompt)
        self.assertTrue(cleared)

    def test_expired_controls_render_as_expired(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            state = build_control_state(
                session_id="sess-expired",
                source="aegis_api",
                source_event="loop_signal",
                fallback=False,
                confidence="moderate",
                escalation="none",
                control={"retry_limit": 1, "max_files": 3, "allow_refactor": False, "require_validation": True},
                human_controls=["Stop retries"],
                reason="loop",
            )
            state["expires_at"] = "2000-01-01T00:00:00+00:00"
            write_control_state(state, cwd=cwd)
            rendered = render_control_state(cwd=cwd)

        self.assertIn("Status: expired", rendered)
        self.assertIn("Stop retries", rendered)

    def test_summary_and_stats_mention_active_controls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            runtime = cwd / ".aegis"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "session.jsonl").write_text(
                '{"timestamp":"2026-04-25T10:00:00+00:00","type":"local_signal","session_id":"s1","details":{"signal_type":"loop_signal","estimated_calls_avoided":1,"signal_details":{"activity_detected":true}}}\n'
                '{"timestamp":"2026-04-25T10:01:00+00:00","type":"aegis_decision","session_id":"s1","details":{"source":"aegis_api","escalation":"none","control":{"max_files":3}}}\n',
                encoding="utf-8",
            )
            write_control_state(
                build_control_state(
                    session_id="s1",
                    source="aegis_api",
                    source_event="loop_signal",
                    fallback=False,
                    confidence="high",
                    escalation="none",
                    control={"retry_limit": 1, "max_files": 3, "allow_refactor": False, "require_validation": True},
                    human_controls=["Stop retries"],
                    reason="loop",
                ),
                cwd=cwd,
            )
            summary = render_summary(cwd=cwd)
            stats = render_stats(cwd=cwd)

        self.assertIn("Active controls issued: present", summary)
        self.assertIn("Active controls issued: present", stats)


class TestControlCli(unittest.TestCase):
    def test_control_cli_commands(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd_before = Path.cwd()
            try:
                os.chdir(tmpdir)
                state = build_control_state(
                    session_id="sess-cli",
                    source="aegis_api",
                    source_event="scope_drift_signal",
                    fallback=False,
                    confidence="high",
                    escalation="medium",
                    control={"retry_limit": 1, "max_files": 3, "allow_refactor": False, "require_validation": True},
                    human_controls=["Stop retries", "Limit changes to 2-3 files"],
                    reason="scope drift",
                )
                write_control_state(state)

                buffer_default = io.StringIO()
                with redirect_stdout(buffer_default):
                    rc_default = main(["control"])
                self.assertEqual(rc_default, 0)
                self.assertIn("Active Controls", buffer_default.getvalue())

                buffer_json = io.StringIO()
                with redirect_stdout(buffer_json):
                    rc_json = main(["control", "--json"])
                self.assertEqual(rc_json, 0)
                parsed = json.loads(buffer_json.getvalue())
                self.assertEqual(parsed["session_id"], "sess-cli")

                buffer_prompt = io.StringIO()
                with redirect_stdout(buffer_prompt):
                    rc_prompt = main(["control", "apply-prompt"])
                self.assertEqual(rc_prompt, 0)
                self.assertIn("Aegis active control state:", buffer_prompt.getvalue())

                buffer_clear = io.StringIO()
                with redirect_stdout(buffer_clear):
                    rc_clear = main(["control", "clear"])
                self.assertEqual(rc_clear, 0)
                self.assertIn("Cleared active control state.", buffer_clear.getvalue())
                self.assertFalse(control_state_path().exists())
            finally:
                os.chdir(cwd_before)
