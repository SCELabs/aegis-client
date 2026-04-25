import subprocess
import unittest

from aegis.shell.observe import collect_repo_observation, parse_diff_stat


class TestShellObserve(unittest.TestCase):
    def test_parse_diff_stat_summary(self):
        diff_stat = (
            "a.py | 2 +-\n"
            "b.py | 5 +++--\n"
            "2 files changed, 4 insertions(+), 3 deletions(-)"
        )
        parsed = parse_diff_stat(diff_stat)
        self.assertEqual(parsed["files_changed"], 2)
        self.assertEqual(parsed["insertions"], 4)
        self.assertEqual(parsed["deletions"], 3)

    def test_collect_repo_observation_uses_git_outputs(self):
        responses = {
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="feature/test\n",
                stderr="",
            ),
            ("git", "status", "--short"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=" M aegis/client.py\n?? new_file.py\n",
                stderr="",
            ),
            ("git", "diff", "--stat"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="aegis/client.py | 3 ++-\n1 file changed, 2 insertions(+), 1 deletion(-)\n",
                stderr="",
            ),
            ("git", "diff", "--numstat"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="2\t1\taegis/client.py\n",
                stderr="",
            ),
        }

        def fake_runner(args, **kwargs):
            return responses[tuple(args)]

        obs = collect_repo_observation(cwd="/tmp/repo", runner=fake_runner)

        self.assertEqual(obs.branch, "feature/test")
        self.assertEqual(obs.changed_file_count, 2)
        self.assertTrue(obs.dirty)
        self.assertEqual(obs.diff_summary["files_changed"], 1)
        self.assertEqual(obs.diff_summary["insertions"], 2)
        self.assertEqual(obs.diff_summary["deletions"], 1)

    def test_collect_repo_observation_handles_non_repo(self):
        def fake_runner(args, **kwargs):
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="fatal")

        obs = collect_repo_observation(cwd="/tmp/missing", runner=fake_runner)
        self.assertEqual(obs.branch, "unknown")
        self.assertEqual(obs.changed_file_count, 0)
        self.assertFalse(obs.dirty)

    def test_collect_repo_observation_ignores_aegis_internal_files(self):
        responses = {
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="feature/test\n",
                stderr="",
            ),
            ("git", "status", "--short"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=" M .aegis/session.jsonl\n M app.py\n?? .aegis/auto_state.json\n",
                stderr="",
            ),
            ("git", "diff", "--stat"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=".aegis/session.jsonl | 2 ++\napp.py | 1 +\n2 files changed, 3 insertions(+)\n",
                stderr="",
            ),
            ("git", "diff", "--numstat"): subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout="2\t0\t.aegis/session.jsonl\n1\t0\tapp.py\n",
                stderr="",
            ),
        }

        def fake_runner(args, **kwargs):
            return responses[tuple(args)]

        obs = collect_repo_observation(cwd="/tmp/repo", runner=fake_runner)
        self.assertEqual(obs.changed_file_count, 1)
        self.assertEqual(obs.diff_summary["files_changed"], 1)
        self.assertEqual(obs.diff_summary["insertions"], 1)
