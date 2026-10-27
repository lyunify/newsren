import json
from io import BytesIO
import unittest
from urllib.error import HTTPError

from newsren import synthesis
from newsren.research import ResearchAgent
from tests.test_research import evidence_story


def model_output(cite="S1", text="Acme Orion reports revenue of 100 million dollars."):
    return {name: [{"text": text, "citations": [cite]}]
            for name in ("answer", "student", "educator", "professional")} | {"limitations": ["Full filing was not read."]}


class Response:
    def __init__(self, payload):
        self.payload = payload
        self.stream = BytesIO(json.dumps(payload).encode())
    def read(self, size=-1):
        return self.stream.read(size)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class SynthesisTests(unittest.TestCase):
    def provider(self, opener=None):
        self.assertTrue(hasattr(synthesis, "OpenAISynthesizer"))
        return synthesis.OpenAISynthesizer("test-secret", "test-model", opener=opener)

    def evidence(self):
        return ResearchAgent().run("Acme Orion revenue", [evidence_story()])["evidence"]

    def test_explicit_enable_and_key_and_model_are_all_required(self):
        self.assertTrue(hasattr(synthesis, "OpenAISynthesizer"))
        cls = synthesis.OpenAISynthesizer
        self.assertIsNone(cls.from_env({"OPENAI_API_KEY": "secret", "NEWSREN_OPENAI_MODEL": "m"}))
        self.assertIsNone(cls.from_env({"NEWSREN_ENABLE_MODEL": "1", "OPENAI_API_KEY": "secret"}))
        self.assertIsNotNone(cls.from_env({"NEWSREN_ENABLE_MODEL": "1", "OPENAI_API_KEY": "secret", "NEWSREN_OPENAI_MODEL": "m"}))

    def test_responses_request_has_bounded_output_and_no_retention(self):
        captured = []
        class Opener:
            def open(self, request, timeout):
                captured.append((request, timeout))
                return Response({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(model_output())}]}],
                                 "usage": {"input_tokens": 100, "output_tokens": 50}})
        result = self.provider(Opener()).synthesize("Acme revenue", self.evidence())
        request, timeout = captured[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.openai.com/v1/responses")
        self.assertFalse(payload["store"])
        self.assertEqual(payload["text"]["format"]["type"], "json_schema")
        self.assertLessEqual(payload["max_output_tokens"], 1600)
        self.assertLessEqual(timeout, 20)
        self.assertEqual(result["usage"]["output_tokens"], 50)
        self.assertNotIn("test-secret", json.dumps(result))

    def test_unknown_citation_or_invented_number_is_rejected(self):
        provider = self.provider()
        for data in [model_output("S99"), model_output(text="Acme revenue was 999 million dollars."), model_output(text="Acme revenue was -100 million dollars."), model_output(text="Acme revenue was −100 million dollars.")]:
            with self.assertRaises(ValueError):
                provider.validate(data, self.evidence())

    def test_missing_audience_citation_is_rejected(self):
        data = model_output()
        data["student"][0]["citations"] = []
        with self.assertRaises(ValueError):
            self.provider().validate(data, self.evidence())

    def test_model_input_passages_are_capped_before_sending(self):
        captured = []
        class Opener:
            def open(self, request, timeout):
                captured.append(json.loads(request.data))
                return Response({"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(model_output())}]}]})
        evidence = self.evidence()
        evidence[0]["quote"] += " background" * 10000
        self.provider(Opener()).synthesize("Acme revenue", evidence)
        sent = json.loads(captured[0]["input"])
        self.assertLessEqual(len(sent["evidence"][0]["quote"]), 1200)

    def test_failed_model_does_not_lose_evidence_or_claim_success(self):
        class Broken:
            model = "test-model"
            def synthesize(self, *args):
                raise ValueError("invalid citations")
        run = ResearchAgent(synthesizer=Broken()).run("Acme Orion revenue", [evidence_story()], use_model=True)
        self.assertEqual(run["synthesis"]["status"], "failed")
        self.assertTrue(run["evidence"])
        self.assertEqual(run["answer"][0]["kind"], "quotation")
        self.assertTrue(any("Model" in note for note in run["limitations"]))

    def test_provider_quota_error_preserves_quotes_and_pending_review_without_retry(self):
        calls = []
        error_body = BytesIO(json.dumps({"error": {"code": "credit_balance_exhausted", "message": "test-secret"}}).encode())
        class OutOfQuota:
            def open(self, request, timeout):
                calls.append(request.full_url)
                raise HTTPError(request.full_url, 429, "Too Many Requests", {}, error_body)
        run = ResearchAgent(synthesizer=self.provider(OutOfQuota())).run("Acme Orion revenue", [evidence_story()], use_model=True)
        self.assertEqual(len(calls), 1)
        self.assertTrue(error_body.closed)
        self.assertEqual(run["synthesis"]["status"], "failed")
        self.assertEqual(run["answer"][0]["kind"], "quotation")
        self.assertEqual(run["answer"][0]["citations"], ["S1"])
        self.assertEqual(run["review"]["status"], "pending")
        self.assertEqual(run["metrics"]["model_calls"], 1)
        self.assertNotIn("test-secret", json.dumps(run))

    def test_valid_model_creates_cited_audience_outputs_pending_review(self):
        class Working:
            model = "test-model"
            def synthesize(self, question, evidence):
                data = model_output()
                data["usage"] = {"input_tokens": 100, "output_tokens": 50}
                return data
        run = ResearchAgent(synthesizer=Working()).run("Acme Orion revenue", [evidence_story()], use_model=True)
        self.assertEqual(run["synthesis"]["status"], "complete")
        self.assertEqual(run["explanations"]["student"][0]["citations"], ["S1"])
        self.assertEqual(run["answer"][0]["kind"], "model_synthesis")
        self.assertEqual(run["review"]["status"], "pending")
        self.assertEqual(run["metrics"]["model_calls"], 1)


if __name__ == "__main__":
    unittest.main()
