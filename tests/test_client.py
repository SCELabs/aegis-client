import unittest
from unittest.mock import Mock, patch

from aegis import AegisClient
from aegis.exceptions import AegisAPIError


class TestAegisClient(unittest.TestCase):
    def setUp(self):
        self.client = AegisClient(
            api_key="test-key",
            base_url="http://127.0.0.1:8000",
            timeout=5.0,
        )

    @patch("aegis.client.requests.post")
    def test_stabilize_sends_expected_request(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "stable",
            "summary": "System stabilized.",
            "cause": "Drift detected.",
            "actions": ["reduce_temperature"],
            "confidence": 0.82,
            "runtime_config": {
                "temperature": 0.6,
                "top_p": 0.9,
                "prompt_suffix": "Be more consistent."
            },
            "prompt": "Rewritten prompt"
        }
        mock_post.return_value = mock_response

        result = self.client.stabilize(
            system_type="multi_agent",
            base_prompt="You are a support coordination system.",
            symptoms=["agents_disagree", "unstable_workflow"],
            severity="medium",
            policy="multi_agent_alignment",
        )

        self.assertEqual(result["status"], "stable")
        mock_post.assert_called_once()

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["system_type"], "multi_agent")
        self.assertEqual(
            kwargs["json"]["base_prompt"],
            "You are a support coordination system."
        )
        self.assertEqual(
            kwargs["json"]["symptoms"],
            ["agents_disagree", "unstable_workflow"]
        )
        self.assertEqual(kwargs["json"]["severity"], "medium")
        self.assertEqual(kwargs["json"]["policy"], "multi_agent_alignment")
        self.assertEqual(
            kwargs["headers"]["Authorization"],
            "Bearer test-key"
        )

    @patch("aegis.client.requests.post")
    def test_stabilize_with_runtime_sets_include_runtime(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "stable",
            "runtime_config": {"temperature": 0.5}
        }
        mock_post.return_value = mock_response

        self.client.stabilize_with_runtime(
            system_type="single_agent",
            base_prompt="You are a careful assistant.",
            symptoms=["drift"],
            severity="low",
        )

        _, kwargs = mock_post.call_args
        self.assertTrue(kwargs["json"]["include_runtime"])

    @patch("aegis.client.requests.post")
    def test_auto_calls_runtime_path(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "stable",
            "runtime_config": {"temperature": 0.4}
        }
        mock_post.return_value = mock_response

        result = self.client.auto(
            system_type="multi_agent",
            base_prompt="Coordinate agents carefully.",
            symptoms=["agents_disagree"],
            severity="high",
            policy="multi_agent_alignment",
        )

        self.assertEqual(result["status"], "stable")

        _, kwargs = mock_post.call_args
        self.assertTrue(kwargs["json"]["include_runtime"])
        self.assertEqual(kwargs["json"]["policy"], "multi_agent_alignment")

    @patch("aegis.client.requests.post")
    def test_header_injection(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"status": "stable"}
        mock_post.return_value = mock_response

        self.client.stabilize(
            system_type="single_agent",
            base_prompt="Prompt",
            symptoms=["drift"],
            severity="low",
        )

        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")

    @patch("aegis.client.requests.post")
    def test_api_error_raises_exception(self, mock_post):
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal server error"}
        mock_post.return_value = mock_response

        with self.assertRaises(AegisAPIError) as ctx:
            self.client.stabilize(
                system_type="single_agent",
                base_prompt="Prompt",
                symptoms=["drift"],
                severity="low",
            )

        self.assertIn("Internal server error", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
