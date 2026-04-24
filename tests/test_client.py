import unittest
from unittest.mock import Mock, patch

import requests

from aegis import AegisClient, AegisConfig, AegisResult
from aegis.exceptions import AegisAPIError, AegisConnectionError, AegisTimeoutError


class TestAegisConfig(unittest.TestCase):
    def test_defaults(self):
        config = AegisConfig()
        self.assertEqual(config.mode, "balanced")
        self.assertEqual(config.max_interventions, 3)
        self.assertTrue(config.allow_retries)
        self.assertTrue(config.allow_retrieval_expansion)
        self.assertTrue(config.allow_context_reduction)
        self.assertTrue(config.allow_prompt_shaping)
        self.assertEqual(config.fallback, "baseline")
        self.assertFalse(config.explain)
        self.assertFalse(config.emit_trace)
        self.assertIsNone(config.policy)
        self.assertEqual(config.timeout_ms, 30_000)


class TestAegisResult(unittest.TestCase):
    def test_helpers(self):
        result = AegisResult(
            output={"text": "ok"},
            final_answer="ok",
            actions=[{"type": "retry"}],
            trace=[{"event": "start"}, {"event": "done"}],
            used_fallback=True,
            explanation="Applied fallback.",
            scope="llm",
            metrics={"latency_ms": 42},
            scope_data={"model": "x"},
        )

        payload = result.to_dict()
        self.assertEqual(payload["scope"], "llm")
        self.assertEqual(payload["actions"], [{"type": "retry"}])
        self.assertEqual(payload["trace"], [{"event": "start"}, {"event": "done"}])
        self.assertEqual(payload["metrics"], {"latency_ms": 42})
        self.assertTrue(payload["used_fallback"])
        self.assertEqual(payload["scope_data"], {"model": "x"})

        self.assertIn("scope=llm", result.debug_summary())

        log = result.to_log_record()
        self.assertEqual(log["trace_steps"], 2)
        self.assertTrue(log["used_fallback"])
        self.assertEqual(log["metrics"], {"latency_ms": 42})

    def test_from_dict_applies_safe_defaults(self):
        result = AegisResult.from_dict({"scope": "rag"})

        self.assertEqual(result.scope, "rag")
        self.assertEqual(result.actions, [])
        self.assertEqual(result.trace, [])
        self.assertEqual(result.metrics, {})
        self.assertFalse(result.used_fallback)
        self.assertEqual(result.scope_data, {})


class TestAegisClient(unittest.TestCase):
    def setUp(self):
        self.config = AegisConfig(mode="aggressive", timeout_ms=7000, explain=True)
        self.client = AegisClient(
            api_key="test-key",
            base_url="https://aegis-backend-production-4b47.up.railway.app",
            config=self.config,
        )

    def test_client_construction_and_auto_facade_cache(self):
        self.assertEqual(self.client.api_key, "test-key")
        self.assertEqual(self.client.timeout, 7.0)

        auto_a = self.client.auto()
        auto_b = self.client.auto()
        self.assertIs(auto_a, auto_b)

    @patch("aegis.client.requests.post")
    def test_llm_scope_call(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "output": {"text": "hello"},
            "final_answer": "hello",
            "metrics": {"latency_ms": 99},
            "actions": [{"type": "prompt_shape"}],
            "trace": [{"event": "start"}],
            "used_fallback": False,
            "explanation": "Stabilized prompt behavior.",
            "scope_data": {"model": "gpt"},
        }
        mock_post.return_value = mock_response

        result = self.client.auto().llm(
            base_prompt="You are careful.",
            symptoms=["inconsistent_outputs"],
            severity="medium",
        )

        self.assertIsInstance(result, AegisResult)
        self.assertEqual(result.scope, "llm")
        self.assertEqual(result.final_answer, "hello")

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["timeout"], 7.0)
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(kwargs["json"]["scope"], "llm")
        self.assertEqual(kwargs["json"]["config"]["mode"], "aggressive")

    @patch("aegis.client.requests.post")
    def test_rag_scope_call(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"scope": "rag", "output": "ok"}
        mock_post.return_value = mock_response

        result = self.client.auto().rag(
            query="What changed?",
            retrieved_context=["Doc A", "Doc B"],
            symptoms=["hallucinated_references"],
            severity="medium",
        )

        self.assertEqual(result.scope, "rag")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["query"], "What changed?")

    @patch("aegis.client.requests.post")
    def test_step_scope_call(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"scope": "step", "used_fallback": True}
        mock_post.return_value = mock_response

        result = self.client.auto().step(
            step_name="triage",
            step_input={"ticket": 1},
            symptoms=["routing_instability"],
            severity="high",
        )

        self.assertEqual(result.scope, "step")
        self.assertTrue(result.used_fallback)

    @patch("aegis.client.requests.post")
    def test_context_scope_call_defaults(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"scope": "context", "scope_data": {"cleaned_messages": []}}
        mock_post.return_value = mock_response

        result = self.client.auto().context(
            objective="Clean context",
            messages=[{"role": "user", "content": "Hello"}],
            tool_results=[{"tool": "search", "ok": True}],
            constraints=["be concise"],
        )

        self.assertEqual(result.scope, "context")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["objective"], "Clean context")
        self.assertEqual(kwargs["json"]["messages"], [{"role": "user", "content": "Hello"}])
        self.assertEqual(kwargs["json"]["tool_results"], [{"tool": "search", "ok": True}])
        self.assertEqual(kwargs["json"]["constraints"], ["be concise"])
        self.assertEqual(kwargs["json"]["symptoms"], ["context_noise"])
        self.assertEqual(kwargs["json"]["severity"], "medium")
        self.assertEqual(kwargs["json"]["metadata"], {})
        self.assertTrue(mock_post.call_args.args[0].endswith("/v1/auto/context"))

    @patch("aegis.client.requests.post")
    def test_agent_scope_call_defaults(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"scope": "agent", "scope_data": {"steps": []}}
        mock_post.return_value = mock_response

        result = self.client.auto().agent(goal="Resolve ticket")

        self.assertEqual(result.scope, "agent")
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["goal"], "Resolve ticket")
        self.assertEqual(kwargs["json"]["steps"], [])
        self.assertEqual(kwargs["json"]["tools"], [])
        self.assertEqual(kwargs["json"]["symptoms"], ["unstable_workflow"])
        self.assertEqual(kwargs["json"]["severity"], "medium")
        self.assertEqual(kwargs["json"]["metadata"], {})
        self.assertNotIn("max_steps", kwargs["json"])
        self.assertTrue(mock_post.call_args.args[0].endswith("/v1/auto/agent"))

    @patch("aegis.client.requests.post")
    def test_agent_session_id_and_max_steps(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"scope": "agent"}
        mock_post.return_value = mock_response

        self.client.auto().agent(
            goal="Handle workflow",
            session_id="sess-1",
            max_steps=6,
            metadata={"run_id": "r-9"},
        )

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["metadata"]["session_id"], "sess-1")
        self.assertEqual(payload["metadata"]["run_id"], "r-9")
        self.assertEqual(payload["max_steps"], 6)

    @patch("aegis.client.requests.post")
    def test_agent_does_not_override_existing_session_id(self, mock_post):
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"scope": "agent"}
        mock_post.return_value = mock_response

        self.client.auto().agent(
            goal="Handle workflow",
            session_id="sess-new",
            metadata={"session_id": "sess-existing"},
        )

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["metadata"]["session_id"], "sess-existing")

    @patch("aegis.client.requests.post")
    def test_context_unsupported_scope_does_not_fallback(self, mock_post):
        not_found = Mock()
        not_found.ok = False
        not_found.status_code = 404
        not_found.json.return_value = {"detail": "Not found"}
        mock_post.return_value = not_found

        with self.assertRaises(AegisAPIError) as ctx:
            self.client.auto().context(objective="Clean context")

        self.assertIn("does not support the 'context' auto scope", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 1)
        self.assertTrue(mock_post.call_args.args[0].endswith("/v1/auto/context"))

    @patch("aegis.client.requests.post")
    def test_agent_unsupported_scope_does_not_fallback(self, mock_post):
        method_not_allowed = Mock()
        method_not_allowed.ok = False
        method_not_allowed.status_code = 405
        method_not_allowed.json.return_value = {"detail": "Method not allowed"}
        mock_post.return_value = method_not_allowed

        with self.assertRaises(AegisAPIError) as ctx:
            self.client.auto().agent(goal="Run plan")

        self.assertIn("does not support the 'agent' auto scope", str(ctx.exception))
        self.assertEqual(mock_post.call_count, 1)
        self.assertTrue(mock_post.call_args.args[0].endswith("/v1/auto/agent"))

    @patch("aegis.client.requests.post")
    def test_fallback_to_stabilize_path(self, mock_post):
        not_found = Mock()
        not_found.ok = False
        not_found.status_code = 404
        not_found.json.return_value = {"detail": "Not found"}

        ok = Mock()
        ok.ok = True
        ok.json.return_value = {"output": "ok"}

        mock_post.side_effect = [not_found, ok]

        result = self.client.auto().rag(
            query="Policy",
            retrieved_context=["doc"],
            symptoms=["drift"],
            severity="low",
        )

        self.assertEqual(result.scope, "rag")
        first_url = mock_post.call_args_list[0].args[0]
        second_url = mock_post.call_args_list[1].args[0]
        self.assertTrue(first_url.endswith("/v1/auto/rag"))
        self.assertTrue(second_url.endswith("/v1/stabilize"))

        fallback_payload = mock_post.call_args_list[1].kwargs["json"]
        self.assertEqual(fallback_payload["system_type"], "rag")
        self.assertEqual(fallback_payload["base_prompt"], "Policy")
        self.assertEqual(fallback_payload["metadata"]["retrieved_context"], ["doc"])
        self.assertTrue(fallback_payload["include_runtime"])

    @patch("aegis.client.requests.post", side_effect=requests.Timeout)
    def test_timeout_error(self, _):
        with self.assertRaises(AegisTimeoutError):
            self.client.auto().llm(
                base_prompt="Prompt",
                symptoms=["drift"],
                severity="low",
            )

    @patch("aegis.client.requests.post", side_effect=requests.ConnectionError)
    def test_connection_error(self, _):
        with self.assertRaises(AegisConnectionError):
            self.client.auto().llm(
                base_prompt="Prompt",
                symptoms=["drift"],
                severity="low",
            )

    @patch("aegis.client.requests.post")
    def test_api_error(self, mock_post):
        bad = Mock()
        bad.ok = False
        bad.status_code = 500
        bad.json.return_value = {"detail": "backend failed"}
        mock_post.return_value = bad

        with self.assertRaises(AegisAPIError) as ctx:
            self.client.auto().llm(
                base_prompt="Prompt",
                symptoms=["drift"],
                severity="low",
            )

        self.assertIn("backend failed", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
