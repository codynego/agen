import json
from unittest.mock import Mock, patch

from django.test import SimpleTestCase, override_settings

from .llm.openai_gateway import OpenAIModelGateway
from .llm.openai_gateway import ModelGatewayError
from .llm.router import ModelRouter
from .llm.types import AgentIdentity, TaskAnalysis


IDENTITY = AgentIdentity(
    name="Nova",
    network_handle="agen-123456789abc",
    agent_id="00000000-0000-0000-0000-000000000001",
    trust_level="developing",
    capabilities=["plan", "research"],
)


def analysis(**overrides):
    values = {
        "intent_type": "task",
        "capabilities": ["restaurant_search", "reservation"],
        "location": "Lagos",
        "risk_level": "low",
        "requires_clarification": False,
        "task_brief": "Reserve a table in Lagos.",
        "complexity": "simple",
        "user_response": "I can help coordinate that reservation.",
    }
    values.update(overrides)
    return TaskAnalysis(**values)


class OpenAIModelGatewayTests(SimpleTestCase):
    @patch("apps.agents.llm.openai_gateway.urlopen")
    def test_structured_analysis_uses_responses_api_without_storage(self, mocked_urlopen):
        body = {
            "output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": json.dumps(analysis().__dict__)}],
            }]
        }
        response = Mock()
        response.read.return_value = json.dumps(body).encode("utf-8")
        mocked_urlopen.return_value.__enter__.return_value = response
        gateway = OpenAIModelGateway("test-key", "https://api.openai.test/v1", timeout_seconds=7)

        result = gateway.analyze_task("Reserve a restaurant", "gpt-5-mini", IDENTITY)

        self.assertEqual(result.capabilities, ["restaurant_search", "reservation"])
        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "gpt-5-mini")
        self.assertFalse(payload["store"])
        self.assertTrue(payload["text"]["format"]["strict"])
        self.assertIn('"name": "Nova"', payload["instructions"])
        self.assertIn('"network_handle": "agen-123456789abc"', payload["instructions"])
        self.assertEqual(mocked_urlopen.call_args.kwargs["timeout"], 7)

    @patch("apps.agents.llm.openai_gateway.urlopen")
    def test_business_chat_uses_only_supplied_identity_and_context(self, mocked_urlopen):
        response = Mock()
        response.read.return_value = json.dumps({
            "output": [{"type": "message", "content": [{"type": "output_text", "text": "You can return it within seven days."}]}]
        }).encode("utf-8")
        mocked_urlopen.return_value.__enter__.return_value = response
        gateway = OpenAIModelGateway("test-key", "https://api.openai.test/v1")

        result = gateway.generate_business_reply(
            "Can I return this?",
            "gpt-5-mini",
            {"name": "Acme Guide", "company_name": "Acme Ltd"},
            [{"title": "Returns", "content": "Unused items may be returned within seven days."}],
        )

        self.assertEqual(result, "You can return it within seven days.")
        payload = json.loads(mocked_urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertFalse(payload["store"])
        self.assertIn("Acme Guide", payload["instructions"])
        self.assertIn("Unused items", payload["instructions"])

    @override_settings(AGENT_DEFAULT_MODEL="gpt-5-mini", AGENT_REASONING_MODEL="gpt-5.1")
    def test_complex_requests_escalate_to_reasoning_model(self):
        gateway = Mock()
        gateway.analyze_task.side_effect = [analysis(complexity="complex"), analysis(complexity="complex")]

        result = ModelRouter(gateway).analyze_task("Plan a multi-country business trip", IDENTITY)

        self.assertEqual(result.complexity, "complex")
        self.assertEqual(
            [call.args[1] for call in gateway.analyze_task.call_args_list],
            ["gpt-5-mini", "gpt-5.1"],
        )
        self.assertTrue(all(call.args[2] == IDENTITY for call in gateway.analyze_task.call_args_list))

    @override_settings(AGENT_DEFAULT_MODEL="gpt-5-mini", AGENT_REASONING_MODEL="gpt-5.1")
    def test_simple_requests_use_only_default_model(self):
        gateway = Mock()
        gateway.analyze_task.return_value = analysis()

        ModelRouter(gateway).analyze_task("Find a restaurant", IDENTITY)

        gateway.analyze_task.assert_called_once_with("Find a restaurant", "gpt-5-mini", IDENTITY)

    @override_settings(AGENT_DEFAULT_MODEL="gpt-5-mini", AGENT_REASONING_MODEL="gpt-5.1")
    def test_gateway_failure_returns_deterministic_fallback_signal(self):
        gateway = Mock()
        gateway.analyze_task.side_effect = ModelGatewayError("OpenAI network connection failed: proxy refused")

        with self.assertLogs("apps.agents.llm.router", level="WARNING") as logs:
            result = ModelRouter(gateway).analyze_task("Find a restaurant", IDENTITY)

        self.assertIsNone(result)
        self.assertIn("proxy refused", logs.output[0])
