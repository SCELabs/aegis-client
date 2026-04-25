import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from aegis.shell.auto import (
    preflight_check,
    render_stats,
    render_status,
    render_summary,
    reset_project_runtime,
    run_auto_mode,
    start_auto_mode_background,
    stop_auto_mode,
)
from aegis.shell.observe import RepoObservation


def _observation(*, changed_files: int = 0, files_changed: int = 0, insertions: int = 0, deletions: int = 0) -> RepoObservation:
    return RepoObservation(
        cwd="C:/repo",
        branch="feature/x",
        status_short="",
        diff_stat="",
        changed_file_count=changed_files,
        dirty=changed_files > 0,
        diff_summary={"files_changed": files_changed, "insertions": insertions, "deletions": deletions},
    )


class TestAutoPreflight(unittest.TestCase):
    @patch("aegis.shell.auto._backend_reachable")
    @patch("aegis.shell.auto._is_git_repo")
    @patch("aegis.shell.auto._runtime_config_sources")
    def test_silent_preflight_success(self, mock_sources, mock_git, mock_backend):
        mock_sources.return_value = (
            {"api_key": "k", "base_url": "http://localhost:8000"},
            {"api_key": "env", "base_url": "env"},
            Path("/tmp/.aegis/config.json"),
            True,
        )
        mock_git.return_value = True
        mock_backend.return_value = "yes"

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            report = preflight_check(cwd="C:/repo", print_messages=False)

        self.assertTrue(report["can_run"])
        self.assertEqual(buffer.getvalue(), "")

    @patch("aegis.shell.auto._backend_reachable")
    @patch("aegis.shell.auto._is_git_repo")
    @patch("aegis.shell.auto._runtime_config_sources")
    def test_missing_api_key_guidance(self, mock_sources, mock_git, mock_backend):
        mock_sources.return_value = (
            {"api_key": None, "base_url": "http://localhost:8000"},
            {"api_key": "missing", "base_url": "default"},
            Path("/tmp/.aegis/config.json"),
            False,
        )
        mock_git.return_value = True
        mock_backend.return_value = "unknown"

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            report = preflight_check(cwd="C:/repo", print_messages=True)

        self.assertTrue(report["can_run"])
        self.assertIn("No API key found", buffer.getvalue())

    @patch("aegis.shell.auto._backend_reachable")
    @patch("aegis.shell.auto._is_git_repo")
    @patch("aegis.shell.auto._runtime_config_sources")
    def test_outside_git_repo_guidance(self, mock_sources, mock_git, mock_backend):
        mock_sources.return_value = (
            {"api_key": "k", "base_url": "http://localhost:8000"},
            {"api_key": "env", "base_url": "env"},
            Path("/tmp/.aegis/config.json"),
            True,
        )
        mock_git.return_value = False
        mock_backend.return_value = "yes"

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            report = preflight_check(cwd="C:/repo", print_messages=True)

        self.assertFalse(report["can_run"])
        self.assertIn("No git repo detected", buffer.getvalue())


class TestDoctorResetStartStopStatus(unittest.TestCase):
    def test_reset_removes_only_project_runtime(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            project_runtime = repo / ".aegis"
            project_runtime.mkdir(parents=True, exist_ok=True)
            (project_runtime / "auto_state.json").write_text("{}", encoding="utf-8")
            global_config = repo / "home" / ".aegis" / "config.json"
            global_config.parent.mkdir(parents=True, exist_ok=True)
            global_config.write_text("{}", encoding="utf-8")

            msg = reset_project_runtime(cwd=repo)
            self.assertIn("Reset project runtime state", msg)
            self.assertFalse(project_runtime.exists())
            self.assertTrue(global_config.exists())

    @patch("aegis.shell.auto.write_auto_state")
    @patch("aegis.shell.auto.subprocess.Popen")
    @patch("aegis.shell.auto.read_auto_state")
    @patch("aegis.shell.auto.preflight_check")
    def test_start_writes_background_state_and_invokes_worker(
        self, mock_preflight, mock_read_state, mock_popen, mock_write_state
    ):
        mock_preflight.return_value = {"can_run": True}
        mock_read_state.return_value = {"running": False}
        proc = Mock()
        proc.pid = 12345
        proc.poll.return_value = None
        mock_popen.return_value = proc

        rc = start_auto_mode_background(interval_seconds=4.0, verbose=True, cwd="C:/repo")

        self.assertEqual(rc, 0)
        command = mock_popen.call_args.args[0]
        self.assertIn("--background-worker", command)
        self.assertIn("--verbose", command)
        payload = mock_write_state.call_args.args[0]
        self.assertEqual(payload["mode"], "background")
        self.assertEqual(payload["pid"], 12345)

    @patch("aegis.shell.auto.os.name", "nt")
    @patch("aegis.shell.auto.write_auto_state")
    @patch("aegis.shell.auto.subprocess.Popen")
    @patch("aegis.shell.auto.read_auto_state")
    @patch("aegis.shell.auto.preflight_check")
    def test_windows_start_uses_no_window_flag_when_available(
        self, mock_preflight, mock_read_state, mock_popen, mock_write_state
    ):
        mock_preflight.return_value = {"can_run": True}
        mock_read_state.return_value = {"running": False}
        proc = Mock()
        proc.pid = 789
        proc.poll.return_value = None
        mock_popen.return_value = proc

        with patch("aegis.shell.auto.subprocess.CREATE_NO_WINDOW", 0x08000000, create=True):
            rc = start_auto_mode_background(interval_seconds=3.0, cwd="C:/repo")

        self.assertEqual(rc, 0)
        creationflags = mock_popen.call_args.kwargs.get("creationflags", 0)
        self.assertTrue(creationflags & 0x08000000)
        self.assertTrue(mock_write_state.called)

    @patch("aegis.shell.auto.subprocess.Popen")
    @patch("aegis.shell.auto.read_auto_state")
    @patch("aegis.shell.auto.preflight_check")
    def test_start_failure_is_graceful(self, mock_preflight, mock_read_state, mock_popen):
        mock_preflight.return_value = {"can_run": True}
        mock_read_state.return_value = {"running": False}
        mock_popen.side_effect = OSError("no detach")

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            rc = start_auto_mode_background(interval_seconds=3.0, cwd="C:/repo")

        self.assertEqual(rc, 1)
        self.assertIn("Background start is unavailable here", buffer.getvalue())

    @patch("aegis.shell.auto.write_auto_state")
    @patch("aegis.shell.auto.read_auto_state")
    def test_stop_handles_no_running_process(self, mock_read_state, mock_write_state):
        mock_read_state.return_value = {"running": False}
        stopped = stop_auto_mode(cwd="C:/repo")
        self.assertFalse(stopped)
        payload = mock_write_state.call_args.args[0]
        self.assertTrue(payload["stop_requested"])

    @patch("aegis.shell.auto.read_all_session_events")
    @patch("aegis.shell.auto.collect_repo_observation")
    @patch("aegis.shell.auto._is_pid_running")
    @patch("aegis.shell.auto.read_auto_state")
    def test_status_shows_background_state(
        self, mock_read_state, mock_pid_running, mock_collect, mock_events
    ):
        mock_read_state.return_value = {
            "running": True,
            "mode": "background",
            "pid": 99,
            "project_path": "C:/repo",
            "last_heartbeat_at": "2099-01-01T00:00:00+00:00",
        }
        mock_pid_running.return_value = True
        mock_collect.return_value = _observation(changed_files=1, files_changed=1, insertions=2)
        mock_events.return_value = [{"type": "auto_started", "details": {}}]

        output = render_status(cwd="C:/repo")
        self.assertIn("Auto mode running: yes", output)
        self.assertIn("Mode: background", output)
        self.assertIn("PID: 99", output)
        self.assertIn("Last heartbeat: 2099-01-01T00:00:00+00:00", output)
        self.assertIn("Worker healthy: yes", output)
        self.assertIn("Project path: C:/repo", output)
        self.assertIn("Session log path:", output)

    @patch("aegis.shell.auto.read_all_session_events")
    @patch("aegis.shell.auto.collect_repo_observation")
    @patch("aegis.shell.auto._is_pid_running")
    @patch("aegis.shell.auto.read_auto_state")
    def test_status_unknown_reason_when_pid_unverifiable(
        self, mock_read_state, mock_pid_running, mock_collect, mock_events
    ):
        mock_read_state.return_value = {"running": True, "mode": "background", "pid": 55, "project_path": "C:/repo"}
        mock_pid_running.return_value = None
        mock_collect.return_value = _observation(changed_files=0, files_changed=0, insertions=0)
        mock_events.return_value = []

        output = render_status(cwd="C:/repo")
        self.assertIn(
            "Auto mode running: unknown (PID recorded, process check unavailable)",
            output,
        )
        self.assertIn(
            "Worker status unknown. Run aegis start again to re-establish monitoring.",
            output,
        )

    @patch("aegis.shell.auto.read_all_session_events")
    @patch("aegis.shell.auto.collect_repo_observation")
    @patch("aegis.shell.auto._is_pid_running")
    @patch("aegis.shell.auto.read_auto_state")
    def test_status_stale_heartbeat_reports_actionable_message(
        self, mock_read_state, mock_pid_running, mock_collect, mock_events
    ):
        mock_read_state.return_value = {
            "running": True,
            "mode": "background",
            "pid": 55,
            "project_path": "C:/repo",
            "last_heartbeat_at": "2000-01-01T00:00:00+00:00",
            "interval_seconds": 2.0,
        }
        mock_pid_running.return_value = True
        mock_collect.return_value = _observation(changed_files=1, files_changed=1, insertions=1)
        mock_events.return_value = []
        output = render_status(cwd="C:/repo")

        self.assertIn("Worker healthy: no", output)
        self.assertIn("[Aegis] Auto mode may not be active. Run aegis start again.", output)


class TestWorkerReliability(unittest.TestCase):
    @patch("aegis.shell.auto.append_auto_event")
    @patch("aegis.shell.auto.time.sleep")
    @patch("aegis.shell.auto.collect_repo_observation")
    @patch("aegis.shell.auto._process_signal_candidate")
    @patch("aegis.shell.auto._build_client")
    @patch("aegis.shell.auto.write_auto_state")
    @patch("aegis.shell.auto.read_auto_state")
    @patch("aegis.shell.auto.preflight_check")
    def test_dirty_startup_baseline_does_not_trigger_immediate_event(
        self,
        mock_preflight,
        mock_read_state,
        mock_write_state,
        mock_build_client,
        mock_process_signal,
        mock_collect,
        mock_sleep,
        mock_append,
    ):
        mock_preflight.return_value = {"can_run": True}
        mock_read_state.side_effect = [
            {"running": False},
            {"running": False},
            {"running": True, "stop_requested": False},
            {"running": True, "stop_requested": True},
        ]
        mock_build_client.return_value = Mock()
        mock_collect.return_value = _observation(changed_files=2, files_changed=2, insertions=4)
        mock_sleep.return_value = None

        rc = run_auto_mode(interval_seconds=2.0, cwd="C:/repo", background_worker=True)
        self.assertEqual(rc, 0)
        self.assertEqual(mock_process_signal.call_count, 0)
        self.assertTrue(mock_write_state.called)
        self.assertTrue(mock_append.called)

    def test_malformed_session_log_lines_do_not_crash_summary_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            runtime = repo / ".aegis"
            runtime.mkdir(parents=True, exist_ok=True)
            (runtime / "session.jsonl").write_text(
                "not-json\n"
                "{\"type\":\"local_signal\",\"session_id\":\"s1\",\"details\":{\"signal_type\":\"loop_signal\",\"estimated_calls_avoided\":1,\"signal_details\":{\"activity_detected\":true}}}\n",
                encoding="utf-8",
            )
            summary = render_summary(cwd=repo)
            stats = render_stats(cwd=repo)

        self.assertTrue(summary.startswith("[Aegis]"))
        self.assertTrue(stats.startswith("[Aegis]"))
        self.assertNotIn("$", summary)
        self.assertNotIn("$", stats)

    @patch("aegis.shell.auto._is_pid_running")
    @patch("aegis.shell.auto.read_auto_state")
    def test_summary_reports_active_monitoring_without_events(self, mock_read_state, mock_pid_running):
        mock_read_state.return_value = {
            "running": True,
            "pid": 333,
            "last_heartbeat_at": "2099-01-01T00:00:00+00:00",
            "project_path": "C:/repo",
        }
        mock_pid_running.return_value = True
        with patch("aegis.shell.auto.read_all_session_events", return_value=[]):
            output = render_summary(cwd="C:/repo")

        self.assertEqual(output, "[Aegis] Monitoring active. No instability events detected yet.")

    @patch("aegis.shell.auto._is_pid_running")
    @patch("aegis.shell.auto.read_auto_state")
    def test_summary_reports_no_active_session_when_not_running(self, mock_read_state, mock_pid_running):
        mock_read_state.return_value = {"running": False, "pid": 0, "project_path": "C:/repo"}
        mock_pid_running.return_value = False
        with patch("aegis.shell.auto.read_all_session_events", return_value=[]):
            output = render_summary(cwd="C:/repo")

        self.assertEqual(output, "[Aegis] No active monitoring session found. Run aegis start.")

    @patch("aegis.shell.auto.preflight_check")
    @patch("aegis.shell.auto._build_client")
    @patch("aegis.shell.auto.collect_repo_observation")
    @patch("aegis.shell.auto.time.sleep")
    def test_worker_session_log_stays_project_local(self, mock_sleep, mock_collect, mock_build_client, mock_preflight):
        mock_preflight.return_value = {"can_run": True}
        mock_build_client.return_value = Mock()
        mock_collect.return_value = _observation(changed_files=0, files_changed=0, insertions=0)
        mock_sleep.return_value = None

        with tempfile.TemporaryDirectory() as tmpdir:
            project_a = Path(tmpdir) / "project-a"
            project_b = Path(tmpdir) / "project-b"
            project_a.mkdir(parents=True, exist_ok=True)
            project_b.mkdir(parents=True, exist_ok=True)
            with patch(
                "aegis.shell.auto.read_auto_state",
                side_effect=[
                    {"running": False, "project_path": str(project_a)},
                    {"running": False, "project_path": str(project_a)},
                    {"running": True, "stop_requested": False, "project_path": str(project_a)},
                    {"running": True, "stop_requested": True, "project_path": str(project_a)},
                ],
            ):
                rc = run_auto_mode(interval_seconds=2.0, cwd=project_a, background_worker=True)
                self.assertEqual(rc, 0)

            session_a = project_a / ".aegis" / "session.jsonl"
            session_b = project_b / ".aegis" / "session.jsonl"
            self.assertTrue(session_a.exists())
            self.assertFalse(session_b.exists())
