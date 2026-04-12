import unittest
from unittest.mock import AsyncMock, Mock, patch

from aegis import AegisClient, AsyncAegisClient
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

    @patch.object(AegisClient, "auto")
    def test_auto_openai_config_applies_runtime(self, mock_auto):
        mock_auto.return_value = {
            "status": "stable",
            "runtime_config": {
                "temperature": 0.3,
                "top_p": 0.95,
                "prompt_suffix": "Be strict and concise."
            },
            "summary": "Stable"
        }

        config = self.client.auto_openai_config(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a support system."},
                {"role": "user", "content": "Handle this case."},
            ],
            symptoms=["policy_drift"],
            severity="medium",
        )

        self.assertEqual(config["model"], "gpt-4o")
        self.assertEqual(config["temperature"], 0.3)
        self.assertEqual(config["top_p"], 0.95)
        self.assertIn("Be strict and concise.", config["messages"][0]["content"])
        self.assertEqual(config["aegis"]["status"], "stable")


class TestAsyncAegisClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = AsyncAegisClient(
            api_key="test-key",
            base_url="http://127.0.0.1:8000",
            timeout=5.0,
        )

    @patch("aegis.client.httpx.AsyncClient")
    async def test_async_stabilize_sends_expected_request(self, mock_async_client):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "stable"}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response

        mock_async_client.return_value.__aenter__.return_value = mock_client_instance
        mock_async_client.return_value.__aexit__.return_value = None

        result = await self.client.stabilize(
            system_type="multi_agent",
            base_prompt="You are a support coordination system.",
            symptoms=["agents_disagree"],
            severity="medium",
            policy="multi_agent_alignment",
        )

        self.assertEqual(result["status"], "stable")
        mock_client_instance.post.assert_awaited_once()

        _, kwargs = mock_client_instance.post.call_args
        self.assertEqual(kwargs["json"]["system_type"], "multi_agent")
        self.assertEqual(kwargs["json"]["policy"], "multi_agent_alignment")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")

    @patch.object(AsyncAegisClient, "auto", new_callable=AsyncMock)
    async def test_async_auto_openai_config_applies_runtime(self, mock_auto):
        mock_auto.return_value = {
            "status": "stable",
            "runtime_config": {
                "temperature": 0.25,
                "top_p": 0.9,
                "prompt_suffix": "Be deterministic."
            },
            "summary": "Stable"
        }

        config = await self.client.auto_openai_config(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a support system."},
                {"role": "user", "content": "Handle this case."},
            ],
            symptoms=["policy_drift"],
            severity="medium",
        )

        self.assertEqual(config["model"], "gpt-4o")
        self.assertEqual(config["temperature"], 0.25)
        self.assertEqual(config["top_p"], 0.9)
        self.assertIn("Be deterministic.", config["messages"][0]["content"])
        self.assertEqual(config["aegis"]["status"], "stable")


if __name__ == "__main__":
    unittest.main()
