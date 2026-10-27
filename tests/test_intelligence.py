import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from newsren import intelligence


class IntelligenceTests(unittest.TestCase):
    def store(self, path):
        self.assertTrue(hasattr(intelligence, "IntelligenceStore"), "Research artifacts require durable storage")
        return intelligence.IntelligenceStore(path)

    def test_evidence_snapshot_and_review_survive_restart(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "research.sqlite3"
            s = self.store(path)
            run = {"id": "a" * 32, "question": "Revenue?", "evidence": [{"id": "S1", "quote": "Revenue was 100."}], "review": {"status": "pending"}}
            s.save_run(run)
            run["evidence"][0]["quote"] = "Overwritten input"
            self.assertEqual(self.store(path).get_run("a" * 32)["evidence"][0]["quote"], "Revenue was 100.")
            s.review_run("a" * 32, "approved", "Checked original filing")
            saved = self.store(path).get_run("a" * 32)
            self.assertEqual(saved["review"]["status"], "approved")
            self.assertEqual(saved["review"]["note"], "Checked original filing")
            self.assertTrue(saved["review"]["reviewed_at"])
            self.assertEqual(len(s.list_runs()), 1)

    def test_invalid_review_and_overwrite_are_rejected(self):
        with TemporaryDirectory() as tmp:
            s = self.store(Path(tmp) / "runs.sqlite3")
            run = {"id": "b" * 32, "question": "Q", "review": {"status": "pending"}}
            s.save_run(run)
            with self.assertRaises(ValueError):
                s.save_run(run)
            with self.assertRaises(ValueError):
                s.review_run("b" * 32, "published", "")
            with self.assertRaises(KeyError):
                s.review_run("c" * 32, "approved", "")


if __name__ == "__main__":
    unittest.main()
