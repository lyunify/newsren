import json
import unittest
from io import BytesIO
from urllib.error import HTTPError

from newsren import synthesis
from newsren.research import ResearchAgent
from newsren.research_pages import render_research_index
from tests.test_research import evidence_story
from tests.test_synthesis import Response, model_output


class Transport:
    def __init__(self, output=None, stop_reason="end_turn"):
        self.calls = []
        self.output = output or model_output()
        self.stop_reason = stop_reason

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        return Response({"type": "message", "stop_reason": self.stop_reason,
                         "content": [{"type": "text", "text": json.dumps(self.output)}],
                         "usage": {"input_tokens": 100, "output_tokens": 50}})


class ClaudeTests(unittest.TestCase):
    def provider(self, transport=None):
        self.assertTrue(hasattr(synthesis, "AnthropicSynthesizer"))
        return synthesis.AnthropicSynthesizer("claude-test-secret", "test-claude", opener=transport or Transport())

    def evidence(self):
        return ResearchAgent().run("Acme Orion revenue", [evidence_story()])["evidence"]

    def test_explicit_selection_never_falls_back_to_another_provider(self):
        self.assertTrue(hasattr(synthesis, "synthesizer_from_env"))
        config = {"NEWSREN_ENABLE_MODEL": "1", "NEWSREN_MODEL_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": "secret", "NEWSREN_ANTHROPIC_MODEL": "test-claude", "OPENAI_API_KEY": "other-secret", "NEWSREN_OPENAI_MODEL": "test-openai"}
        self.assertEqual(synthesis.synthesizer_from_env(config).provider, "anthropic")
        self.assertIsNone(synthesis.synthesizer_from_env({**config, "ANTHROPIC_API_KEY": ""}))
        self.assertIsNone(synthesis.synthesizer_from_env({**config, "NEWSREN_ENABLE_MODEL": "0"}))
        self.assertIsNone(synthesis.synthesizer_from_env({**config, "NEWSREN_ANTHROPIC_MODEL": ""}))
        self.assertIsNone(synthesis.synthesizer_from_env({**config, "NEWSREN_MODEL_PROVIDER": "unknown"}))
        self.assertEqual(synthesis.synthesizer_from_env({k:v for k,v in config.items() if k != "NEWSREN_MODEL_PROVIDER"}).provider, "openai")

    def test_messages_request_is_bounded_and_returns_validated_usage(self):
        transport = Transport()
        result = self.provider(transport).synthesize("Acme revenue", self.evidence())
        request, timeout = transport.calls[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.get_header("Authorization"), "Bearer claude-test-secret")
        self.assertEqual(request.get_header("Anthropic-version"), "2023-06-01")
        self.assertEqual(payload["output_config"]["format"]["type"], "json_schema")
        self.assertLessEqual(payload["max_tokens"], 1600)
        self.assertLessEqual(timeout, 20)
        self.assertNotIn("store", payload)
        sent = json.loads(payload["messages"][0]["content"])
        self.assertEqual(sent["evidence"][0]["id"], "S1")
        self.assertEqual(result["usage"], {"input_tokens":100, "output_tokens":50, "total_tokens":150})
        self.assertNotIn("claude-test-secret", json.dumps(result))

    def test_unknown_citations_and_new_numbers_are_rejected(self):
        for output in (model_output("P99"), model_output(text="Acme revenue was 999 million dollars.")):
            with self.assertRaises(ValueError):
                self.provider(Transport(output)).synthesize("Acme revenue", self.evidence())

    def test_truncated_and_refused_responses_are_not_successful(self):
        for reason in ("max_tokens", "refusal", "tool_use"):
            with self.assertRaises(ValueError):
                self.provider(Transport(stop_reason=reason)).synthesize("Acme revenue", self.evidence())

    def test_success_records_actual_provider_and_awaits_human_review(self):
        run = ResearchAgent(synthesizer=self.provider()).run("Acme Orion revenue", [evidence_story()], use_model=True)
        self.assertEqual(run["synthesis"]["status"], "complete")
        self.assertEqual(run["synthesis"]["provider"], "anthropic")
        self.assertEqual(run["answer"][0]["kind"], "model_synthesis")
        self.assertEqual(run["review"]["status"], "pending")
        self.assertNotIn("claude-test-secret", json.dumps(run))

    def test_quota_error_is_closed_and_preserves_cited_quotes_without_retry(self):
        calls, body = [], BytesIO(b'{"error":{"message":"claude-test-secret"}}')
        class OutOfQuota:
            def open(self, request, timeout):
                calls.append(request)
                raise HTTPError(request.full_url, 400, "Bad Request", {}, body)
        run = ResearchAgent(synthesizer=self.provider(OutOfQuota())).run("Acme Orion revenue", [evidence_story()], use_model=True)
        self.assertEqual(len(calls), 1)
        self.assertTrue(body.closed)
        self.assertEqual(run["synthesis"]["status"], "failed")
        self.assertEqual(run["answer"][0]["citations"], ["S1"])
        self.assertNotIn("claude-test-secret", json.dumps(run))

    def test_consent_names_the_actual_provider_and_escapes_the_label(self):
        html = render_research_index([],model_enabled=True,model_provider="Anthropic (Claude)")
        self.assertIn("to Anthropic (Claude)",html)
        self.assertNotIn("to OpenAI",html)
        self.assertNotIn("<script>bad</script>",render_research_index([],model_enabled=True,model_provider="<script>bad</script>"))


if __name__ == "__main__":
    unittest.main()
