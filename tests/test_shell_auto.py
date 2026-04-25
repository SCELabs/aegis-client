import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from aegis.shell.auto import (
    AutoHeuristicEngine,
    DecisionOutcome,
    _process_signal_candidate,
    _should_emit_signal_output,
    _startup_banner,
    process_signal_candidate,
    render_summary,
)
from aegis.shell.observe import RepoObservation
from aegis.shell.session import append_auto_event, read_all_session_events


def _observation(*, changed_files: int, files_changed: int, insertions: int, deletions: int = 0) -> RepoObservation:
    return RepoObservation(
        cwd="C:/repo",
        branch="feature/auto",
        status_short=" M a.py",
        diff_stat=f"{files_changed} files changed, {insertions} insertions(+), {deletions} deletions(-)",
        changed_file_count=changed_files,
        dirty=changed_files > 0,
        diff_summary={
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
        },
    )


class TestAutoHeuristics(unittest.TestCase):
    def test_explanations_are_contextual(self):
        engine = AutoHeuristicEngine()
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=4))
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=4))
        loop_signal = engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=4))[0]

        fake_result = Mock()
        fake_result.actions = [{"type": "stabilize_system"}]
        fake_result.explanation = "Selected because it achieved the highest overall score."
        fake_result.trace = []
        fake_result.metrics = {}
        fake_result.scope_data = {}
        client = Mock()
        client.auto.return_value.step.return_value = fake_result

        output = process_signal_candidate(
            client=client,
            observation=_observation(changed_files=1, files_changed=1, insertions=4),
            signal=loop_signal,
            previous_snapshot=engine.previous_snapshot,
            session_id="sess-why",
            issue_counts={},
        )

        self.assertIn("No progress detected across multiple iterations", output)
        self.assertNotIn("highest overall score", output)

    def test_impact_is_observable_when_no_activity(self):
        engine = AutoHeuristicEngine()
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        loop_signal = engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))[0]

        fake_result = Mock()
        fake_result.actions = []
        fake_result.explanation = "any"
        fake_result.trace = []
        fake_result.metrics = {}
        fake_result.scope_data = {}
        client = Mock()
        client.auto.return_value.step.return_value = fake_result

        output = process_signal_candidate(
            client=client,
            observation=_observation(changed_files=1, files_changed=1, insertions=3),
            signal=loop_signal,
            previous_snapshot=engine.previous_snapshot,
            session_id="sess-impact",
            issue_counts={},
        )

        self.assertIn("Impact:", output)
        self.assertIn("Estimated AI iterations avoided: 3", output)
        self.assertIn("Prevented retries: range unavailable", output)
        self.assertIn("Reduced scope from 1 files to 3", output)
        self.assertNotIn("$", output)


class TestNoiseSuppression(unittest.TestCase):
    def test_duplicate_message_suppression_and_minimal_second_message(self):
        state = {}
        outcome = DecisionOutcome(
            full_output="[Aegis] Full",
            minimal_output="[Aegis] Repeat",
            signal_type="loop_signal",
            escalation="none",
            confidence="moderate",
            state_fingerprint=(3, None, None, None, None, "none"),
        )

        emit_first, msg_first = _should_emit_signal_output(outcome=outcome, display_state=state, now_ts=1.0)
        emit_second, msg_second = _should_emit_signal_output(outcome=outcome, display_state=state, now_ts=2.0)
        emit_third, msg_third = _should_emit_signal_output(outcome=outcome, display_state=state, now_ts=3.0)

        self.assertTrue(emit_first)
        self.assertEqual(msg_first, "[Aegis] Full")
        self.assertTrue(emit_second)
        self.assertEqual(msg_second, "[Aegis] Repeat")
        self.assertFalse(emit_third)
        self.assertEqual(msg_third, "")

    def test_escalation_replaces_repetition(self):
        state = {}
        base = DecisionOutcome(
            full_output="[Aegis] Base",
            minimal_output="[Aegis] Repeat",
            signal_type="loop_signal",
            escalation="none",
            confidence="moderate",
            state_fingerprint=(3, None, None, None, None, "none"),
        )
        high = DecisionOutcome(
            full_output="[Aegis] Escalated",
            minimal_output="[Aegis] Repeat",
            signal_type="loop_signal",
            escalation="high",
            confidence="high",
            state_fingerprint=(3, None, None, None, None, "high"),
        )

        _should_emit_signal_output(outcome=base, display_state=state, now_ts=1.0)
        _should_emit_signal_output(outcome=base, display_state=state, now_ts=2.0)
        emit_high, msg_high = _should_emit_signal_output(outcome=high, display_state=state, now_ts=3.0)

        self.assertTrue(emit_high)
        self.assertEqual(msg_high, "[Aegis] Escalated")

    def test_escalated_issue_uses_short_line_not_full_block(self):
        state = {}
        escalated = DecisionOutcome(
            full_output="[Aegis] Full escalated block",
            minimal_output="[Aegis] Loop detected still present - escalation monitoring active.",
            signal_type="loop_signal",
            escalation="high",
            confidence="high",
            state_fingerprint=(3, None, None, None, None, "high"),
        )

        emit_first, msg_first = _should_emit_signal_output(outcome=escalated, display_state=state, now_ts=1.0)
        emit_second, msg_second = _should_emit_signal_output(outcome=escalated, display_state=state, now_ts=2.0)

        self.assertTrue(emit_first)
        self.assertIn("Full escalated block", msg_first)
        self.assertTrue(emit_second)
        self.assertIn("still present - escalation monitoring active", msg_second)
        self.assertNotIn("Full escalated block", msg_second)


class TestLoggingAndSummary(unittest.TestCase):
    def test_decision_logging_contains_structured_fields(self):
        engine = AutoHeuristicEngine()
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        signal = engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))[0]

        fake_result = Mock()
        fake_result.actions = [{"type": "increase_coordination_constraints"}]
        fake_result.explanation = "any"
        fake_result.trace = []
        fake_result.metrics = {}
        fake_result.scope_data = {}
        client = Mock()
        client.auto.return_value.step.return_value = fake_result

        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            _process_signal_candidate(
                client=client,
                observation=_observation(changed_files=1, files_changed=1, insertions=3),
                signal=signal,
                previous_snapshot=engine.previous_snapshot,
                session_id="sess-log",
                issue_counts={"loop_signal": 2},
                cwd=cwd,
            )
            events = read_all_session_events(cwd=cwd)

        decision = [event for event in events if event.get("type") == "aegis_decision"][0]["details"]
        self.assertIn("control", decision)
        self.assertIn("confidence", decision)
        self.assertIn("escalation", decision)
        self.assertIn("impact_estimate", decision)

    def test_summary_uses_activity_for_observable_impact(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            append_auto_event(
                event_type="local_signal",
                details={
                    "signal_type": "loop_signal",
                    "estimated_calls_avoided": 3,
                    "signal_details": {"activity_detected": False},
                },
                session_id="sess-1",
                cwd=cwd,
            )
            append_auto_event(
                event_type="aegis_decision",
                details={"source": "aegis_api", "escalation": "none"},
                session_id="sess-1",
                cwd=cwd,
            )
            output = render_summary(cwd=cwd)

        self.assertIn("Estimated AI iterations avoided: 0", output)
        self.assertIn("Prevented retries: none observed", output)
        self.assertIn("Scope reduction: no scope-limiting intervention recorded", output)
        self.assertNotIn("$", output)
        self.assertNotIn("{", output)

    def test_summary_pluralization_uses_time_for_one(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            append_auto_event(
                event_type="local_signal",
                details={
                    "signal_type": "loop_signal",
                    "estimated_calls_avoided": 3,
                    "signal_details": {"activity_detected": True},
                },
                session_id="sess-1",
                cwd=cwd,
            )
            append_auto_event(
                event_type="aegis_decision",
                details={"source": "aegis_api", "escalation": "none"},
                session_id="sess-1",
                cwd=cwd,
            )
            output = render_summary(cwd=cwd)

        self.assertIn("Loop detected (1 time)", output)
        self.assertIn("Scope drift detected (0 times)", output)

    def test_summary_uses_auto_started_for_active_session_without_signals(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cwd = Path(tmpdir)
            append_auto_event(
                event_type="auto_started",
                details={"project_path": str(cwd)},
                session_id="sess-started",
                cwd=cwd,
            )
            (cwd / ".aegis" / "auto_state.json").write_text(
                '{"running": true, "pid": 99, "last_heartbeat_at": "2099-01-01T00:00:00+00:00"}',
                encoding="utf-8",
            )
            with unittest.mock.patch("aegis.shell.auto._is_pid_running", return_value=True):
                output = render_summary(cwd=cwd)

        self.assertEqual(output, "[Aegis] Monitoring active. No instability events detected yet.")

    def test_structured_control_hidden_by_default_and_shown_in_verbose(self):
        engine = AutoHeuristicEngine()
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))
        signal = engine.evaluate(_observation(changed_files=1, files_changed=1, insertions=3))[0]

        fake_result = Mock()
        fake_result.actions = [{"type": "increase_coordination_constraints"}]
        fake_result.explanation = "any"
        fake_result.trace = []
        fake_result.metrics = {}
        fake_result.scope_data = {}
        client = Mock()
        client.auto.return_value.step.return_value = fake_result

        default_output = process_signal_candidate(
            client=client,
            observation=_observation(changed_files=1, files_changed=1, insertions=3),
            signal=signal,
            previous_snapshot=engine.previous_snapshot,
            session_id="sess-default",
            issue_counts={},
        )
        verbose_output = process_signal_candidate(
            client=client,
            observation=_observation(changed_files=1, files_changed=1, insertions=3),
            signal=signal,
            previous_snapshot=engine.previous_snapshot,
            session_id="sess-verbose",
            issue_counts={},
            verbose=True,
        )

        self.assertNotIn("Control (structured):", default_output)
        self.assertIn("Control (structured):", verbose_output)


class TestBanner(unittest.TestCase):
    def test_startup_banner_human_readable(self):
        banner = _startup_banner()
        self.assertIn("Auto mode active", banner)
        self.assertIn("Watching for:", banner)
        self.assertIn("retry loops", banner)
        self.assertNotIn("{", banner)
