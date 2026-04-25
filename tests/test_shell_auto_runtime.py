import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

from aegis.shell.auto import run_auto_mode
from aegis.shell.observe import RepoObservation


def _observation(*, changed_files: int, files_changed: int, insertions: int, deletions: int = 0) -> RepoObservation:
    return RepoObservation(
        cwd="C:/repo",
        branch="feature/auto",
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


class TestAutoRuntimeHardening(unittest.TestCase):
    def test_no_issue_message_printed_once_per_session(self):
        with (
            patch("aegis.shell.auto.preflight_check", return_value={"can_run": True}),
            patch("aegis.shell.auto.append_auto_event") as mock_append,
            patch("aegis.shell.auto.time.sleep"),
            patch("aegis.shell.auto.time.time", side_effect=[0.0, 11.0, 12.0, 13.0]),
            patch(
                "aegis.shell.auto.collect_repo_observation",
                side_effect=[
                    _observation(changed_files=0, files_changed=0, insertions=0),
                    _observation(changed_files=0, files_changed=0, insertions=0),
                    _observation(changed_files=0, files_changed=0, insertions=0),
                ],
            ),
            patch("aegis.shell.auto._build_client", return_value=Mock()),
            patch("aegis.shell.auto.write_auto_state") as mock_write_state,
            patch(
                "aegis.shell.auto.read_auto_state",
                side_effect=[
                    {"running": False},
                    {"running": True, "stop_requested": False},
                    {"running": True, "stop_requested": False},
                    {"running": True, "stop_requested": False},
                    {"running": True, "stop_requested": True},
                ],
            ),
        ):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_auto_mode(interval_seconds=2.0, cwd="C:/repo")

        self.assertEqual(rc, 0)
        self.assertEqual(buffer.getvalue().count("No issues detected yet - monitoring workflow."), 1)
        self.assertTrue(mock_write_state.called)
        self.assertTrue(mock_append.called)

    def test_stale_stop_signal_cleared_on_startup(self):
        with (
            patch("aegis.shell.auto.preflight_check", return_value={"can_run": True}),
            patch("aegis.shell.auto.append_auto_event") as mock_append,
            patch("aegis.shell.auto.time.sleep"),
            patch("aegis.shell.auto.collect_repo_observation", return_value=_observation(changed_files=0, files_changed=0, insertions=0)),
            patch("aegis.shell.auto._build_client", return_value=Mock()),
            patch("aegis.shell.auto.write_auto_state") as mock_write_state,
            patch(
                "aegis.shell.auto.read_auto_state",
                side_effect=[{"running": True, "stop_requested": True}, {"running": True, "stop_requested": True}],
            ),
        ):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_auto_mode(interval_seconds=2.0, cwd="C:/repo")

        self.assertEqual(rc, 0)
        first_write_payload = mock_write_state.call_args_list[0].args[0]
        self.assertTrue(first_write_payload["running"])
        self.assertFalse(first_write_payload["stop_requested"])
        self.assertNotIn("already running", buffer.getvalue().lower())
        self.assertTrue(mock_append.called)

    def test_loop_persists_across_normal_file_changes(self):
        with (
            patch("aegis.shell.auto.preflight_check", return_value={"can_run": True}),
            patch("aegis.shell.auto.append_auto_event") as mock_append,
            patch("aegis.shell.auto.time.sleep"),
            patch("aegis.shell.auto._build_client", return_value=Mock()),
            patch("aegis.shell.auto.write_auto_state") as mock_write_state,
            patch(
                "aegis.shell.auto.read_auto_state",
                side_effect=[
                    {"running": False},
                    {"running": True, "stop_requested": False},
                    {"running": True, "stop_requested": False},
                    {"running": True, "stop_requested": True},
                ],
            ),
            patch(
                "aegis.shell.auto.collect_repo_observation",
                side_effect=[
                    _observation(changed_files=1, files_changed=1, insertions=1),
                    _observation(changed_files=2, files_changed=2, insertions=3),
                ],
            ) as mock_collect,
        ):
            rc = run_auto_mode(interval_seconds=2.0, cwd="C:/repo")

        self.assertEqual(rc, 0)
        self.assertEqual(mock_collect.call_count, 2)
        self.assertTrue(mock_write_state.called)
        self.assertTrue(mock_append.called)

    def test_clean_shutdown_only_on_explicit_stop(self):
        with (
            patch("aegis.shell.auto.preflight_check", return_value={"can_run": True}),
            patch("aegis.shell.auto.append_auto_event") as mock_append,
            patch("aegis.shell.auto.time.sleep"),
            patch("aegis.shell.auto._build_client", return_value=Mock()),
            patch("aegis.shell.auto.write_auto_state") as mock_write_state,
            patch(
                "aegis.shell.auto.read_auto_state",
                side_effect=[
                    {"running": False},
                    {"running": True, "stop_requested": False},
                    {"running": False, "stop_requested": False},
                    {"running": True, "stop_requested": True},
                ],
            ),
            patch(
                "aegis.shell.auto.collect_repo_observation",
                side_effect=[
                    _observation(changed_files=1, files_changed=1, insertions=1),
                    _observation(changed_files=1, files_changed=1, insertions=2),
                ],
            ) as mock_collect,
        ):
            rc = run_auto_mode(interval_seconds=2.0, cwd="C:/repo")

        self.assertEqual(rc, 0)
        self.assertEqual(mock_collect.call_count, 2)
        last_write_payload = mock_write_state.call_args_list[-1].args[0]
        self.assertFalse(last_write_payload["running"])
        self.assertFalse(last_write_payload["stop_requested"])
        self.assertTrue(mock_append.called)

    def test_expected_error_prints_clean_message_without_crash(self):
        with (
            patch("aegis.shell.auto.preflight_check", return_value={"can_run": True}),
            patch("aegis.shell.auto.append_auto_event") as mock_append,
            patch("aegis.shell.auto.time.sleep"),
            patch("aegis.shell.auto._build_client", return_value=Mock()),
            patch("aegis.shell.auto.write_auto_state") as mock_write_state,
            patch(
                "aegis.shell.auto.read_auto_state",
                side_effect=[
                    {"running": False},
                    {"running": True, "stop_requested": False},
                    {"running": True, "stop_requested": False},
                    {"running": True, "stop_requested": True},
                ],
            ),
            patch(
                "aegis.shell.auto.collect_repo_observation",
                side_effect=[RuntimeError("transient failure"), _observation(changed_files=1, files_changed=1, insertions=1)],
            ),
        ):
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                rc = run_auto_mode(interval_seconds=2.0, cwd="C:/repo")

        self.assertEqual(rc, 0)
        self.assertIn("[Aegis] Temporary auto-mode error", buffer.getvalue())
        self.assertTrue(mock_write_state.called)
        self.assertTrue(mock_append.called)
