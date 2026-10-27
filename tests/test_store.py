import threading
import unittest
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory

from newsren.store import Store

LONG = "This item description is long enough to count as a preferred summary sentence."


class ScriptedOpener:
    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.calls = 0

    def open(self, request, timeout=None):
        self.calls += 1
        body = self.bodies.pop(0)
        if isinstance(body, Exception):
            raise body
        return _Response(body)


class _Response:
    def __init__(self, body):
        self.body = body
        self.stream = BytesIO(body)

    def read(self, size=-1):
        return self.stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def feed(url, title):
    xml = f"""<rss><channel><item>
      <title>{title}</title>
      <link>{url}</link>
      <description>{LONG}</description>
      <pubDate>26 Oct 2026 00:00:00 GMT</pubDate>
    </item></channel></rss>"""
    return xml.encode()


class StoreTests(unittest.TestCase):
    def test_failure_keeps_old_items_and_updates_others(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            first = ScriptedOpener([feed("https://example.com/verge", "Verge one")] + [feed(f"https://example.com/{i}", f"Story {i}") for i in range(10)])
            store.refresh(opener=first, now="2026-10-26T01:00:00+00:00")
            self.assertEqual(first.calls, 11)
            titles = {row["title"] for row in store.snapshot()["stories"]}
            self.assertIn("Verge one", titles)
            second_bodies = [RuntimeError("HTTP Error 500")]
            second_bodies.extend(feed(f"https://example.com/new-{i}", f"New {i}") for i in range(10))
            second = ScriptedOpener(second_bodies)
            snapshot = store.refresh(opener=second, now="2026-10-26T02:00:00+00:00")
            titles = {row["title"] for row in snapshot["stories"]}
            self.assertIn("Verge one", titles)
            self.assertIn("New 0", titles)
            self.assertNotIn("Story 0", titles)
            verge = next(row for row in snapshot["sources"] if row["name"] == "The Verge")
            self.assertEqual(verge["last_error"], "RuntimeError: HTTP Error 500")
            self.assertEqual(verge["last_success_at"], "2026-10-26T01:00:00+00:00")
            ars = next(row for row in snapshot["sources"] if row["name"] == "Ars Technica")
            self.assertEqual(ars["last_error"], "")
            self.assertEqual(ars["last_success_at"], "2026-10-26T02:00:00+00:00")

    def test_refresh_calls_do_not_overlap(self):
        class GateOpener:
            def __init__(self):
                self.calls = 0
                self.entered = threading.Event()
                self.release = threading.Event()

            def open(self, request, timeout=None):
                self.calls += 1
                if self.calls == 1:
                    self.entered.set()
                    self.release.wait(2)
                return _Response(b"<rss></rss>")

        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            opener = GateOpener()
            errors = []

            def run():
                try:
                    store.refresh(opener=opener, now="2026-10-26T01:00:00+00:00")
                except Exception as exc:
                    errors.append(exc)

            first = threading.Thread(target=run)
            second = threading.Thread(target=run)
            first.start()
            self.assertTrue(opener.entered.wait(2))
            second.start()
            second.join(0.3)
            self.assertEqual(opener.calls, 1)
            opener.release.set()
            first.join(3)
            second.join(3)
            self.assertEqual(errors, [])

    def test_get_by_id(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            opener = ScriptedOpener([feed("https://example.com/only", "Only story")] + [b"<rss></rss>"] * 10)
            store.refresh(opener=opener, now="2026-10-26T01:00:00+00:00")
            story = store.snapshot()["stories"][0]
            self.assertEqual(store.get(story["id"])["title"], "Only story")
            self.assertIsNone(store.get("0123456789abcdef"))


if __name__ == "__main__":
    unittest.main()
