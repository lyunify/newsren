import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from newsren.store import Store
from tests.test_store import ScriptedOpener, feed


class HistoryTests(unittest.TestCase):
    def test_departed_feed_article_is_retrievable_after_restart(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            store = Store(path)
            store.refresh(opener=ScriptedOpener([feed("https://example.org/old", "Acme Orion first release")] + [b"<rss/>"] * 10), now="2026-10-01T00:00:00Z")
            old = store.snapshot()["stories"][0]
            store.refresh(opener=ScriptedOpener([feed("https://example.org/new", "Acme Orion second release")] + [b"<rss/>"] * 10), now="2026-10-02T00:00:00Z")
            self.assertEqual([s["title"] for s in store.snapshot()["stories"]], ["Acme Orion second release"])
            restarted = Store(path)
            self.assertIsNotNone(restarted.get(old["id"]))
            self.assertEqual(len(restarted.research_stories()), 2)

    def test_same_url_revision_retains_old_content_and_first_seen(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            store = Store(path)
            xml = feed("https://example.org/acme", "Acme Orion earnings")
            xml = xml.replace(b"This item description is long enough to count as a preferred summary sentence.", b"Acme Orion reports revenue of 100 million dollars.")
            store.refresh(opener=ScriptedOpener([xml] + [b"<rss/>"] * 10), now="2026-10-01T00:00:00Z")
            store.refresh(opener=ScriptedOpener([xml] + [b"<rss/>"] * 10), now="2026-10-02T00:00:00Z")
            self.assertEqual(store.snapshot()["stories"][0].get("first_seen_at"), "2026-10-01T00:00:00Z")
            store.refresh(opener=ScriptedOpener([xml.replace(b"100 million", b"200 million")] + [b"<rss/>"] * 10), now="2026-10-03T00:00:00Z")
            rows = Store(path).research_stories()
            self.assertEqual(len(rows), 2)
            old = next(row for row in rows if "100 million" in row["excerpt"])
            self.assertIn("200 million", store.get(store.snapshot()["stories"][0]["id"])["excerpt"])
            self.assertNotEqual(old["id"], store.snapshot()["stories"][0]["id"])
            self.assertEqual(Store(path).get(old["id"])["excerpt"], "Acme Orion reports revenue of 100 million dollars.")

    def test_new_store_can_read_original_cache_format(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            path.write_text('{"stories": [], "sources": {}}')
            self.assertEqual(Store(path).research_stories(), [])

    def test_recurring_content_never_overwrites_first_occurrence(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            store = Store(path)
            base = feed("https://example.org/acme", "Acme Orion earnings")
            base = base.replace(b"This item description is long enough to count as a preferred summary sentence.", b"Acme Orion revenue was AMOUNT million dollars.")
            for day, amount in enumerate((b"100", b"200", b"100", b"200"), 1):
                store.refresh(opener=ScriptedOpener([base.replace(b"AMOUNT", amount)] + [b"<rss/>"] * 10), now=f"2026-10-0{day}T00:00:00Z")
            rows = Store(path).research_stories()
            hundred = [row for row in rows if "100 million" in row["excerpt"]]
            self.assertEqual(sorted(row["first_seen_at"] for row in hundred), ["2026-10-01T00:00:00Z", "2026-10-03T00:00:00Z"])
