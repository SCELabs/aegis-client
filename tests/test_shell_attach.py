import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from aegis.shell.attach import AttachSignal, run_attach
from aegis.shell.cli import _build_parser, main
from aegis.shell.observe import RepoObservation
from aegis.shell.session import read_all_session_events


def _observation(*, changed_files: int = 0, files_changed: int = 0, insertions: int = 0, deletions: int = 0) -> RepoObservation:
    return RepoObservation(
        cwd="C:/repo",
        branch="feature/attach",
        status_short="",
        diff_stat="",
        changed_file_count=changed_files,
        dirty=changed_files > 0,
        diff_summary={"files_changed": files_changed, "insertions": insertions, "deletions": deletions},
    )


class _FakePopen:
    def __init__(self, *, stdout_lines: list[str], stderr_lines: list[str], returncode: int = 0):
        self.stdout = io.StringIO("".join(f"{line}\n" for line in stdout_lines))
        self.stderr = io.StringIO("".join(f"{line}\n" for line in stderr_lines))
        self.returncode = returncode
        self._poll_calls = 0

    def poll(self):
        self._poll_calls += 1
        if self._poll_calls < 3:
            return None
        return self.returncode


class TestAttachCliAndParser(unittest.TestCase):
    def test_parser_accepts_attach_command(self):
        parser = _build_parser()
        args = parser.parse_args(["attach", "--cmd", "echo hello"])
        self.assertEqual(args.command, "attach")
        self.assertEqual(args.cmd, "echo hello")

    def test_main_attach_invokes_handler(self):
        with patch("aegis.shell.cli.run_attach", return_value=(0, "[Aegis] Pipeline Simulation Report")) as mock_run:
            rc = main(["attach", "--cmd", "echo hello", "--no-live"])
        self.assertEqual(rc, 0)
        self.assertTrue(mock_run.called)


class TestAttachRuntime(unittest.TestCase):
    def test_attach_runs_simple_command_successfully(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=Mock()),
            ):
                rc, report = run_attach(command="echo attach-ok", live_output=False, cwd=cwd)

        self.assertEqual(rc, 0)
        self.assertIn("Pipeline Simulation Report", report)
        self.assertIn("Exit status: 0", report)

    def test_attach_captures_nonzero_exit_code(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch("aegis.shell.attach.subprocess.Popen", return_value=_FakePopen(stdout_lines=["failed"], stderr_lines=[], returncode=7)),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                rc, report = run_attach(command="fake", live_output=False, cwd=cwd)

        self.assertEqual(rc, 0)
        self.assertIn("Exit status: 7", report)

    def test_attach_detects_repeated_retry_lines(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch(
                    "aegis.shell.attach.subprocess.Popen",
                    return_value=_FakePopen(stdout_lines=["retrying request", "retrying request", "retry"], stderr_lines=[]),
                ),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                _, report = run_attach(command="fake", live_output=False, cwd=cwd)

        self.assertIn("Repeated retry patterns:", report)
        self.assertIn("Aegis would have:", report)

    def test_attach_detects_validation_failures(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch(
                    "aegis.shell.attach.subprocess.Popen",
                    return_value=_FakePopen(stdout_lines=["validation failed", "schema error"], stderr_lines=[]),
                ),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                _, report = run_attach(command="fake", live_output=False, cwd=cwd)

        self.assertIn("Validation failures observed: 2", report)

    def test_attach_detects_context_bloat_lines(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch(
                    "aegis.shell.attach.subprocess.Popen",
                    return_value=_FakePopen(stdout_lines=["context length exceeded", "too many tokens"], stderr_lines=[]),
                ),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                _, report = run_attach(command="fake", live_output=False, cwd=cwd)

        self.assertIn("Pipeline Simulation Report", report)

    def test_attach_writes_session_events(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch("aegis.shell.attach.subprocess.Popen", return_value=_FakePopen(stdout_lines=["retry"], stderr_lines=[])),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                run_attach(command="fake", live_output=False, cwd=cwd)
                events = read_all_session_events(cwd=cwd)

        event_types = [event.get("type") for event in events]
        self.assertIn("attach_started", event_types)
        self.assertIn("attach_observed", event_types)
        self.assertIn("attach_completed", event_types)

    def test_attach_writes_control_state_when_signal_detected(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        forced_signal = AttachSignal(
            signal_type="loop_signal",
            severity_candidate="medium",
            message="Retry loop observed",
            details={"activity_detected": True, "changed_files": 4, "file_growth": 2},
            estimated_iterations_avoided=4,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch(
                    "aegis.shell.attach.subprocess.Popen",
                    return_value=_FakePopen(stdout_lines=["retry", "retry", "validation failed"], stderr_lines=[]),
                ),
                patch("aegis.shell.attach._build_attach_signals", return_value=[forced_signal]),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation(changed_files=4, files_changed=4, insertions=4)),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
                patch("aegis.shell.auto.write_control_state") as mock_write_control_state,
            ):
                run_attach(command="fake", live_output=False, cwd=cwd)
                control_path = cwd / ".aegis" / "control.json"
                self.assertTrue(mock_write_control_state.called)

        if control_path.exists():
            payload = json.loads(control_path.read_text(encoding="utf-8"))
            self.assertIn("controls", payload)
            self.assertIn("source", payload)

    def test_attach_report_includes_required_sections(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch("aegis.shell.attach.subprocess.Popen", return_value=_FakePopen(stdout_lines=["retry", "retry"], stderr_lines=[])),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation(changed_files=2, files_changed=2, insertions=2)),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                _, report = run_attach(command="fake", live_output=False, cwd=cwd)

        self.assertIn("Observed:", report)
        self.assertIn("Projected impact:", report)
        self.assertIn("Recommended integration points:", report)

    def test_attach_json_output_is_valid(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch("aegis.shell.attach.subprocess.Popen", return_value=_FakePopen(stdout_lines=["retry"], stderr_lines=[])),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                _, output = run_attach(command="fake", as_json=True, live_output=False, cwd=cwd)

        payload = json.loads(output)
        self.assertIn("observed", payload)
        self.assertIn("projected_impact", payload)
        self.assertIn("recommended_integration_points", payload)

    def test_attach_log_option_reads_existing_log(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            log_path = cwd / "pipeline.log"
            log_path.write_text("retrying\nvalidation failed\n", encoding="utf-8")
            with (
                patch("aegis.shell.attach.subprocess.Popen", return_value=_FakePopen(stdout_lines=[], stderr_lines=[])),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation()),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                _, report = run_attach(command="fake", log_path=log_path, live_output=False, cwd=cwd)

        self.assertIn("Repeated retry patterns: 1", report)
        self.assertIn("Validation failures observed: 1", report)

    def test_attach_does_not_require_backend_when_fallback_used(self):
        fake_client = Mock()
        fake_client.auto.return_value.step.side_effect = RuntimeError("offline")
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            with (
                patch("aegis.shell.attach.subprocess.Popen", return_value=_FakePopen(stdout_lines=["retry", "retry"], stderr_lines=[])),
                patch("aegis.shell.attach.collect_repo_observation", return_value=_observation(changed_files=2, files_changed=2)),
                patch("aegis.shell.attach._build_client", return_value=fake_client),
            ):
                rc, report = run_attach(command="fake", live_output=False, cwd=cwd)

        self.assertEqual(rc, 0)
        self.assertIn("Pipeline Simulation Report", report)
