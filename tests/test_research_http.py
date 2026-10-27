import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from newsren.store import Store
from tests.http_support import serve
from tests.test_research import evidence_story


class ResearchHTTPTests(unittest.TestCase):
    def test_research_form_to_cited_run_to_persisted_human_review(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            a, b = evidence_story("a" * 16), evidence_story("b" * 16, "200", "Ars Technica")
            store.stories = [a, b]
            with serve(store) as base:
                with urlopen(base + "/") as response:
                    self.assertIn('href="/research"', response.read().decode())
                body = urlencode({"question": "Acme Orion revenue", "story_id": a["id"], "use_model": "1"}).encode()
                with urlopen(Request(base + "/research", data=body)) as response:
                    run_url = response.url
                    html = response.read().decode()
                self.assertRegex(run_url, r"/research/[0-9a-f]{32}$")
                self.assertIn("100 million", html)
                self.assertIn("200 million", html)
                self.assertIn('id="S1"', html)
                self.assertIn("numeric_difference", html)
                self.assertIn("pending", html)
                run_id = run_url.rsplit("/", 1)[-1]
                with urlopen(base + "/api/research/" + run_id) as response:
                    saved = json.load(response)
                self.assertEqual(saved["question"], "Acme Orion revenue")
                self.assertEqual(saved["metrics"]["retrieval_calls"], 0)
                self.assertEqual(saved["synthesis"]["status"], "not_configured")
                review = urlencode({"run_id": run_id, "status": "approved", "note": "Read original sources"}).encode()
                with urlopen(Request(base + "/review", data=review)) as response:
                    self.assertIn("Read original sources", response.read().decode())
            # A fresh handler/database connection must retain both evidence and review.
            with serve(Store(Path(tmp) / "cache.json")) as base:
                with urlopen(base + "/api/research/" + run_id) as response:
                    saved = json.load(response)
                self.assertEqual(saved["review"]["status"], "approved")
                self.assertEqual(saved["evidence"][0]["quote"], "Acme Orion reports revenue of 100 million dollars.")

    def test_cross_origin_review_and_oversized_question_are_rejected(self):
        with TemporaryDirectory() as tmp:
            with serve(Store(Path(tmp) / "cache.json")) as base:
                for path, data, headers, expected in [
                    ("/review", b"status=approved", {"Origin": "https://evil.invalid"}, 403),
                    ("/research", urlencode({"question": "a" * 1001}).encode(), {}, 400),
                    ("/research", b"a" * 17000, {}, 413),
                ]:
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(Request(base + path, data=data, headers=headers))
                    self.assertEqual(caught.exception.code, expected)
                    caught.exception.close()

    def test_source_text_cannot_inject_html_in_research(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            a = evidence_story("a" * 16)
            a["excerpt"] = "Acme revenue <script>alert(1)</script> was reported."
            store.stories = [a]
            with serve(store) as base:
                with urlopen(Request(base + "/research", data=b"question=Acme+revenue")) as response:
                    html = response.read().decode()
                self.assertNotIn("<script>alert(1)</script>", html)
                self.assertIn("&lt;script&gt;", html)


if __name__ == "__main__":
    unittest.main()
