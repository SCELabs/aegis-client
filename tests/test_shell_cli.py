import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from aegis.shell.cli import main
from aegis.shell.observe import RepoObservation


class _FakeResult:
    def __init__(self, *, output=None, final_answer=None, explanation="ok"):
        self.output = output
        self.final_answer = final_answer
        self.explanation = explanation
        self.actions = [{"type": "stabilize"}]

    def summary(self):
        return "Scope: step\nActions: 1 runtime controls"

    def debug_summary(self):
        return "scope=step actions=1 trace_steps=0 used_fallback=no"


def _observation() -> RepoObservation:
    return RepoObservation(
        cwd="C:/repo",
        branch="feature/aegis-shell",
        status_short=" M aegis/client.py",
        diff_stat="aegis/client.py | 3 ++-\n1 file changed, 2 insertions(+), 1 deletion(-)",
        changed_file_count=1,
        dirty=True,
        diff_summary={"files_changed": 1, "insertions": 2, "deletions": 1},
    )


class TestShellCLI(unittest.TestCase):
    @patch("aegis.shell.cli.write_user_config")
    @patch("aegis.shell.cli.requests.post")
    @patch("aegis.shell.cli.prompt_email")
    def test_init_command(self, mock_prompt_email, mock_post, mock_write_config):
        mock_prompt_email.return_value = "dev@example.com"
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"api_key": "api-123"}
        mock_post.return_value = mock_response
        mock_write_config.return_value = Path("/tmp/.aegis/config.json")

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = main(["init", "--base-url", "http://localhost:8000"])

        self.assertEqual(rc, 0)
        mock_post.assert_called_once()
        self.assertEqual(mock_post.call_args.kwargs["json"], {"email": "dev@example.com"})
        self.assertTrue(mock_post.call_args.args[0].endswith("/v1/onboard"))
        mock_write_config.assert_called_once_with(api_key="api-123", base_url="http://localhost:8000")

    @patch("aegis.shell.cli.append_session_event")
    @patch("aegis.shell.cli.collect_repo_observation")
    @patch("aegis.shell.cli.AegisClient")
    @patch("aegis.shell.cli.resolve_runtime_config")
    def test_diagnose_command(self, mock_resolve, mock_client_cls, mock_collect, mock_append):
        mock_resolve.return_value = {"api_key": "k", "base_url": "http://localhost:8000"}
        mock_collect.return_value = _observation()

        fake_result = _FakeResult(explanation="Repo is dirty.")
        mock_auto = Mock()
        mock_auto.step.return_value = fake_result
        mock_client = Mock()
        mock_client.auto.return_value = mock_auto
        mock_client_cls.return_value = mock_client

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = main(["diagnose"])

        self.assertEqual(rc, 0)
        kwargs = mock_auto.step.call_args.kwargs
        self.assertEqual(kwargs["step_name"], "dev_repo_diagnosis")
        self.assertEqual(kwargs["symptoms"], ["unstable_workflow"])
        self.assertEqual(kwargs["severity"], "medium")
        mock_append.assert_called_once()

    @patch("aegis.shell.cli.append_session_event")
    @patch("aegis.shell.cli.collect_repo_observation")
    @patch("aegis.shell.cli.AegisClient")
    @patch("aegis.shell.cli.resolve_runtime_config")
    def test_plan_command(self, mock_resolve, mock_client_cls, mock_collect, mock_append):
        mock_resolve.return_value = {"api_key": "k", "base_url": "http://localhost:8000"}
        mock_collect.return_value = _observation()
        fake_result = _FakeResult(final_answer="1. Inspect\n2. Implement\n3. Verify")
        mock_auto = Mock()
        mock_auto.step.return_value = fake_result
        mock_client = Mock()
        mock_client.auto.return_value = mock_auto
        mock_client_cls.return_value = mock_client

        rc = main(["plan", "Refactor parser"])
        self.assertEqual(rc, 0)

        kwargs = mock_auto.step.call_args.kwargs
        self.assertEqual(kwargs["step_name"], "dev_task_plan")
        self.assertEqual(kwargs["step_input"]["task"], "Refactor parser")
        self.assertIn("repo_observation", kwargs["step_input"])
        mock_append.assert_called_once()

    @patch("aegis.shell.cli.append_session_event")
    @patch("aegis.shell.cli.collect_repo_observation")
    @patch("aegis.shell.cli.AegisClient")
    @patch("aegis.shell.cli.resolve_runtime_config")
    def test_review_command(self, mock_resolve, mock_client_cls, mock_collect, mock_append):
        obs = _observation()
        obs.changed_file_count = 7
        obs.diff_summary["files_changed"] = 7
        mock_resolve.return_value = {"api_key": "k", "base_url": "http://localhost:8000"}
        mock_collect.return_value = obs
        fake_result = _FakeResult(explanation="Scope drift risk is medium.")
        mock_auto = Mock()
        mock_auto.context.return_value = fake_result
        mock_client = Mock()
        mock_client.auto.return_value = mock_auto
        mock_client_cls.return_value = mock_client

        rc = main(["review"])
        self.assertEqual(rc, 0)
        kwargs = mock_auto.context.call_args.kwargs
        self.assertEqual(kwargs["severity"], "medium")
        self.assertEqual(kwargs["objective"], "Assess repository scope drift risk and recommend the next action.")
        mock_append.assert_called_once()

    @patch("aegis.shell.cli.append_session_event")
    @patch("aegis.shell.cli.read_recent_session_events")
    @patch("aegis.shell.cli.collect_repo_observation")
    def test_handoff_command_writes_markdown(self, mock_collect, mock_read_recent, mock_append):
        mock_collect.return_value = _observation()
        mock_read_recent.return_value = [
            {"timestamp": "2026-04-24T10:00:00Z", "command": "diagnose", "result_debug_summary": "scope=step"},
            {"timestamp": "2026-04-24T10:10:00Z", "command": "plan", "task": "Ship shell", "result_debug_summary": "scope=step"},
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path.cwd()
            try:
                os_cwd = Path(tmpdir)

                os.chdir(os_cwd)
                rc = main(["handoff"])
                self.assertEqual(rc, 0)
                handoff_path = os_cwd / ".aegis" / "handoff.md"
                self.assertTrue(handoff_path.exists())
                content = handoff_path.read_text(encoding="utf-8")
                self.assertIn("# Aegis Handoff", content)
                self.assertIn("Ship shell", content)
            finally:
                os.chdir(cwd)

        mock_append.assert_called_once()

    @patch("aegis.shell.cli.stop_auto_mode")
    def test_stop_command(self, mock_stop):
        mock_stop.return_value = True
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = main(["stop"])
        self.assertEqual(rc, 0)
        self.assertIn("[Aegis] Stop signal sent.", buffer.getvalue())

    @patch("aegis.shell.cli.render_status")
    def test_status_command(self, mock_render_status):
        mock_render_status.return_value = "[Aegis] Auto mode running: no"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = main(["status"])
        self.assertEqual(rc, 0)
        self.assertIn("[Aegis] Auto mode running: no", buffer.getvalue())

    @patch("aegis.shell.cli.render_summary")
    @patch("aegis.shell.cli.render_stats")
    def test_summary_and_stats_commands(self, mock_render_stats, mock_render_summary):
        mock_render_summary.return_value = "[Aegis] Aegis Summary (Session)"
        mock_render_stats.return_value = "[Aegis] Aegis Stats (All Sessions)"

        summary_buffer = io.StringIO()
        with redirect_stdout(summary_buffer):
            summary_rc = main(["summary"])

        stats_buffer = io.StringIO()
        with redirect_stdout(stats_buffer):
            stats_rc = main(["stats"])

        self.assertEqual(summary_rc, 0)
        self.assertEqual(stats_rc, 0)
        self.assertNotIn("{", summary_buffer.getvalue())
        self.assertNotIn("{", stats_buffer.getvalue())

    @patch("aegis.shell.cli.run_auto_mode")
    def test_auto_command_passes_verbose_flag(self, mock_run_auto_mode):
        mock_run_auto_mode.return_value = 0

        rc_default = main(["auto"])
        rc_verbose = main(["auto", "--verbose"])

        self.assertEqual(rc_default, 0)
        self.assertEqual(rc_verbose, 0)
        self.assertEqual(mock_run_auto_mode.call_args_list[0].kwargs["verbose"], False)
        self.assertEqual(mock_run_auto_mode.call_args_list[0].kwargs["background_worker"], False)
        self.assertEqual(mock_run_auto_mode.call_args_list[1].kwargs["verbose"], True)
        self.assertEqual(mock_run_auto_mode.call_args_list[1].kwargs["background_worker"], False)

    @patch("aegis.shell.cli.run_auto_mode")
    def test_auto_background_worker_flag(self, mock_run_auto_mode):
        mock_run_auto_mode.return_value = 0
        rc = main(["auto", "--background-worker"])
        self.assertEqual(rc, 0)
        self.assertEqual(mock_run_auto_mode.call_args.kwargs["background_worker"], True)

    @patch("aegis.shell.cli.start_auto_mode_background")
    def test_start_command(self, mock_start):
        mock_start.return_value = 0
        rc = main(["start", "--interval", "4", "--verbose"])
        self.assertEqual(rc, 0)
        self.assertEqual(mock_start.call_args.kwargs["interval_seconds"], 4.0)
        self.assertEqual(mock_start.call_args.kwargs["verbose"], True)

    @patch("aegis.shell.cli.render_doctor")
    def test_doctor_command(self, mock_render_doctor):
        mock_render_doctor.return_value = "[Aegis] Doctor"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = main(["doctor"])
        self.assertEqual(rc, 0)
        self.assertIn("[Aegis] Doctor", buffer.getvalue())

    @patch("aegis.shell.cli.reset_project_runtime")
    def test_reset_command(self, mock_reset):
        mock_reset.return_value = "[Aegis] Reset project runtime state"
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = main(["reset"])
        self.assertEqual(rc, 0)
        self.assertIn("Reset project runtime state", buffer.getvalue())
