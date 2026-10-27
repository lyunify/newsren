import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from newsren.intelligence import IntelligenceStore
from newsren.research import ResearchAgent
from newsren.research_pages import render_research_index, render_research_run
from tests.test_research import evidence_story


class EditorialRevisionTests(unittest.TestCase):
    def test_english_display_keeps_original_evidence_and_review_history(self):
        with TemporaryDirectory() as tmp:
            store = IntelligenceStore(Path(tmp) / "runs.sqlite3")
            run = ResearchAgent().run("Acme Orion revenue", [evidence_story()])
            run["question"] = "教育研究修订稿"
            run["revision"] = {"kind": "ai_assisted_editorial", "source_run_id": "d" * 32}
            run["review"]["note"] = "等待本人审核"
            store.save_run(run)
            folder = Path(tmp) / "display-copies"
            folder.mkdir()
            (folder / (run["id"] + ".en.json")).write_text(json.dumps({
                "question": "Education research: editorial draft",
                "answer": [{"text": "An English explanation.", "citations": ["S1"]}],
                "review_note": {"original": "等待本人审核", "text": "Awaiting submitter review."},
                "review": {"status": "approved"}, "evidence": [],
            }), encoding="utf-8")
            saved = IntelligenceStore(store.path).get_run(run["id"])
            self.assertEqual(saved["question"], run["question"])
            self.assertEqual(saved["evidence"], run["evidence"])
            html = render_research_run(saved)
            self.assertIn("An English explanation.", html)
            self.assertIn("Awaiting submitter review.", html)
            self.assertIn("Review: pending", html)
            self.assertIn('href="#S1"', html)
            self.assertNotIn("教育研究修订稿", html)
            for review in (False, True):
                self.assertNotIn("教育研究修订稿", render_research_index([saved], review=review))
            store.review_run(run["id"], "rejected", "A later human review")
            later = render_research_run(store.get_run(run["id"]))
            self.assertIn("A later human review", later)
            self.assertIn("Review: rejected", later)
            self.assertNotIn("Awaiting submitter review.", later)

    def test_revision_identifies_editorial_origin_and_keeps_review_pending(self):
        run = ResearchAgent().run("Acme Orion revenue", [evidence_story()])
        parent_id = "d337ef759d7146119b90687be6ae7150"
        run["revision"] = {"kind": "ai_assisted_editorial", "source_run_id": parent_id}
        run["answer"] = [{"text": "An editorial interpretation.", "citations": ["S1"], "kind": "editorial_revision"}]
        html = render_research_run(run)
        self.assertIn("AI-assisted editorial revision", html)
        self.assertIn(f'href="/research/{parent_id}"', html)
        self.assertIn("Review: pending", html)
        self.assertIn('href="#S1"', html)
        self.assertNotIn("Quoted passages with citations.", html)
        self.assertNotIn("Model-written synthesis with checked", html)

    def test_original_model_and_quotation_notes_keep_their_attribution(self):
        run = ResearchAgent().run("Acme Orion revenue", [evidence_story()])
        self.assertIn("Quoted passages with citations.", render_research_run(run))
        run["synthesis"] = {"status": "complete"}
        html = render_research_run(run)
        self.assertIn("Model-written synthesis with checked", html)
        self.assertNotIn("AI-assisted editorial revision", html)


if __name__ == "__main__":
    unittest.main()
