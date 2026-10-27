import unittest

from newsren import research
from newsren.sources import APPROVED_SOURCES


def evidence_story(key="a", amount="100", source="The Verge", title="Acme Orion earnings report"):
    sentence = f"Acme Orion reports revenue of {amount} million dollars."
    return {"id": key, "title": title, "url": "https://example.org/" + key,
            "source_name": source, "category": "technology", "excerpt": sentence,
            "summary_sentences": [sentence], "published_at": "2026-10-01T00:00:00Z",
            "retrieved_at": "2026-10-02T00:00:00Z"}


class ResearchTests(unittest.TestCase):
    def agent(self, **kw):
        self.assertTrue(hasattr(research, "ResearchAgent"), "ResearchAgent must orchestrate real tools")
        return research.ResearchAgent(**kw)

    def test_quotes_have_complete_provenance_and_answer_citations(self):
        a, b = evidence_story(), evidence_story("b", source="Ars Technica")
        run = self.agent().run("What is Acme Orion revenue?", [a, b])
        self.assertEqual(run["status"], "evidence_found")
        self.assertEqual(len(run["evidence"]), 2)
        for e in run["evidence"]:
            self.assertEqual(e["quote"], "Acme Orion reports revenue of 100 million dollars.")
            self.assertEqual(e["published_at"], "2026-10-01T00:00:00Z")
            self.assertEqual(e["retrieved_at"], "2026-10-02T00:00:00Z")
            self.assertEqual(e["span"], {"field": "excerpt", "start": 0, "end": 50})
        valid = {e["id"] for e in run["evidence"]}
        self.assertTrue(run["plan"])
        self.assertGreaterEqual(len(run["steps"]), 3)
        for row in run["answer"]:
            self.assertTrue(set(row["citations"]) <= valid)
            self.assertTrue(row["citations"])
        self.assertTrue(any("independence" in text.lower() for text in run["limitations"]))
        self.assertEqual(run["review"]["status"], "pending")

    def test_numeric_difference_is_flagged_without_deciding_truth(self):
        run = self.agent().run("Acme Orion revenue", [evidence_story(), evidence_story("b", "200", "Ars Technica")])
        self.assertEqual(run["comparisons"][0]["kind"], "numeric_difference")
        self.assertEqual(run["comparisons"][0]["citations"], ["S1", "S2"])
        self.assertNotIn("verified", run["status"])

    def test_empty_evidence_does_not_create_an_answer(self):
        run = self.agent().run("semiconductor exports", [evidence_story()])
        self.assertEqual(run["status"], "insufficient_evidence")
        self.assertEqual(run["answer"], [])
        self.assertTrue(run["limitations"])

    def test_named_subject_excludes_another_company_sharing_a_metric(self):
        unrelated = evidence_story("unrelated", source="BBC Technology", title="Zenith Motors earnings report")
        unrelated["excerpt"] = "Zenith Motors reports revenue of 300 million dollars."
        run = self.agent().run("What is Acme Orion revenue?", [unrelated, evidence_story()])
        self.assertEqual([row["story_id"] for row in run["evidence"]], ["a"])

    def test_question_focus_excludes_entity_only_matches(self):
        unrelated = evidence_story("other", title="Acme Orion executives receive compensation")
        unrelated["excerpt"] = "Acme Orion executives receive high compensation according to the filing."
        focused = evidence_story("energy", title="Acme Orion uses gas for its data centers")
        focused["excerpt"] = "Acme Orion's filing describes a dependency on methane."
        run = self.agent().run("What does the Acme Orion filing say about energy use?", [unrelated, focused])
        self.assertEqual([row["story_id"] for row in run["evidence"]], ["energy"])

    def test_common_instruction_word_is_not_part_of_named_subject(self):
        run = self.agent().run("Summarize Acme Orion revenue", [evidence_story()])
        self.assertEqual(len(run["evidence"]), 1)

    def test_live_fetch_uses_three_approved_feeds_not_question_url(self):
        calls = []
        def fetch(source, now, opener, timeout):
            calls.append((source["url"], timeout))
            return [evidence_story(str(len(calls)), source=source["name"])], ""
        run = self.agent(fetcher=fetch).run("Acme Orion revenue https://evil.invalid/steal", [], live=True)
        allowed = {s["url"] for s in APPROVED_SOURCES}
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(url in allowed and 0 < timeout <= 12 for url, timeout in calls))
        self.assertEqual(run["metrics"]["retrieval_calls"], 3)
        self.assertTrue(run["evidence"])

    def test_live_failure_keeps_cached_evidence(self):
        def fetch(*args, **kwargs):
            return [], "HTTP 503"
        run = self.agent(fetcher=fetch).run("Acme Orion revenue", [evidence_story()], live=True)
        self.assertEqual(run["status"], "evidence_found")
        self.assertTrue(any("503" in text for text in run["limitations"]))

    def test_deadline_stops_additional_retrieval(self):
        clock = [0.0]
        calls = []
        def fetch(source, now, opener, timeout):
            calls.append(source)
            clock[0] += 40
            return [], "timeout"
        run = self.agent(fetcher=fetch, clock=lambda: clock[0]).run("Acme revenue", [], live=True)
        self.assertEqual(len(calls), 1)
        self.assertTrue(run["metrics"]["budget_exhausted"])

    def test_blank_question_is_rejected(self):
        with self.assertRaises(ValueError):
            self.agent().run("   ", [])


if __name__ == "__main__":
    unittest.main()
