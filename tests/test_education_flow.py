import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from newsren.papers import PaperClient
from newsren.research import ResearchAgent
from newsren.store import Store
from tests.http_support import serve
from tests.test_papers import Transport, XML
from tests.test_research import evidence_story


class EducationFlowTests(unittest.TestCase):
    def agent(self):
        return ResearchAgent(paper_client=PaperClient(opener=Transport([XML])))

    def test_primary_study_works_without_rss_and_retains_citations(self):
        run = self.agent().run("Does AI improve learning?", [], paper_id="PMC1234567")
        self.assertEqual(run["status"], "evidence_found")
        self.assertEqual(run["metrics"]["retrieval_calls"], 1)
        self.assertEqual(run["review"]["status"], "pending")
        valid = {row["id"] for row in run["evidence"]}
        for field in list(run["study"]["fields"].values()) + list(run["study"]["outcomes"].values()):
            self.assertTrue(set(field["citations"]) <= valid)
        self.assertFalse(any("Only RSS" in note for note in run["limitations"]))
        self.assertTrue(any("independent" in note.lower() for note in run["limitations"]))

    def test_unavailable_full_text_keeps_saved_news_without_fabricating_study(self):
        class Unavailable:
            request_count = 1
            def fetch(self, identifier, timeout):
                raise ValueError("Full text unavailable")
        run = ResearchAgent(paper_client=Unavailable()).run("Acme revenue", [evidence_story()], paper_id="PMC1234567")
        self.assertEqual(run["status"], "evidence_found")
        self.assertNotIn("study", run)
        self.assertTrue(any("Full text unavailable" in note for note in run["limitations"]))

    def test_education_paper_does_not_mix_in_machine_learning_business_news(self):
        unrelated = evidence_story()
        unrelated["excerpt"] = "Acme improves AI and machine learning for its trading operations."
        related = evidence_story("education", source="EdSurge")
        related.update(category="education", title="AI in school", excerpt="AI may improve learning for students in school.")
        run = self.agent().run("Does AI improve learning?", [unrelated, related], paper_id="PMC1234567")
        news = [row for row in run["evidence"] if row["id"].startswith("S")]
        self.assertEqual([row["story_id"] for row in news], ["education"])
        self.assertFalse(any("no remote retrieval" in step for step in run["plan"]))

    def test_education_paper_refresh_uses_education_feeds(self):
        categories = []
        def fetch(source, now, opener, timeout):
            categories.append(source["category"])
            return [], ""
        agent = self.agent()
        agent.fetcher = fetch
        run = agent.run("Does AI improve learning?", [], paper_id="PMC1234567", live=True)
        self.assertTrue(categories)
        self.assertEqual(set(categories), {"education"})
        self.assertEqual(run["metrics"]["retrieval_calls"], len(categories) + 1)

    def test_paper_identity_is_checked_before_any_feed_fetch(self):
        def forbidden(*args, **kwargs):
            self.fail("Invalid paper IDs must be rejected before retrieval")
        with self.assertRaises(ValueError):
            ResearchAgent(fetcher=forbidden).run("AI learning", [], live=True, paper_id="https://evil.invalid/")

    def test_real_form_persists_study_and_existing_review(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            with serve(store, research_agent=self.agent()) as base:
                with urlopen(base + "/research") as response:
                    self.assertIn('name="paper_id"', response.read().decode())
                body = urlencode({"question": "Does AI improve learning?", "paper_id": "PMC1234567"}).encode()
                with urlopen(Request(base + "/research", data=body)) as response:
                    run_url, html = response.url, response.read().decode()
                self.assertIn("Education study check", html)
                self.assertIn("Participant count", html)
                self.assertIn("Independent test", html)
                self.assertIn("Not established", html)
                self.assertIn("Peer-review status not independently verified", html)
                for audience in ("For students", "For educators", "For parents"):
                    self.assertIn(audience, html)
                run_id = run_url.rsplit("/", 1)[-1]
                with urlopen(base + "/api/research/" + run_id) as response:
                    saved = json.load(response)
                self.assertEqual(saved["study"]["paper"]["pmcid"], "PMC1234567")
                review = urlencode({"run_id": run_id, "status": "rejected", "note": "Need broader evidence"}).encode()
                with urlopen(Request(base + "/review", data=review)) as response:
                    self.assertIn("Need broader evidence", response.read().decode())
                with self.assertRaises(HTTPError) as caught:
                    urlopen(Request(base + "/research", data=urlencode({"question": "AI learning", "paper_id": "https://evil.invalid/"}).encode()))
                self.assertEqual(caught.exception.code, 400)
                caught.exception.close()


if __name__ == "__main__":
    unittest.main()
