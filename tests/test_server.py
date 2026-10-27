import io
import json
import socket
import threading
import time
import unittest
from contextlib import redirect_stderr
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import Request, urlopen

from newsren.store import Store
from server import HOST, INTERVAL_SECONDS, PORT, build_handler, make_server, start_background_refresh


LONG = "An independent benchmark was published for this model in the source excerpt here."


def sample_story():
    return {
        "id": "abc123abc123abcd",
        "title": "Chip report",
        "url": "https://example.com/a",
        "source_name": "Federal Reserve",
        "category": "finance",
        "published_at": "2026-10-26T12:00:00Z",
        "retrieved_at": "2026-10-26T13:00:00+00:00",
        "excerpt": LONG,
        "summary_sentences": [LONG],
        "summary_truncated": False,
    }


class FakeStore:
    def __init__(self):
        self.calls = 0
        self.refreshing = False
        self.stories = []

    def snapshot(self):
        return {"stories": self.stories, "sources": [], "refreshing": self.refreshing}

    def get(self, story_id):
        return None

    def refresh(self, opener=None, now=None):
        self.calls += 1
        self.stories = [{"id": "abc123abc123abcd"}]
        return self.snapshot()


class ServerTests(unittest.TestCase):
    def test_bind_defaults(self):
        self.assertEqual(HOST, "127.0.0.1")
        self.assertEqual(PORT, 8765)
        self.assertEqual(INTERVAL_SECONDS, 1800)

    def test_get_routes_do_not_refresh(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            related = sample_story()
            related["id"] = "def456def456def4"
            related["title"] = "Chip report followup from the source"
            related["source_name"] = "SEC Press Releases"
            related["published_at"] = "2026-10-20T00:00:00Z"
            related["excerpt"] = "A later clause mentions cost for this model in the source excerpt here."
            related["summary_sentences"] = [related["excerpt"]]
            store.stories = [sample_story(), related]
            store.refresh = lambda **kwargs: (_ for _ in ()).throw(AssertionError("refresh"))
            httpd = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(store))
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            port = httpd.server_address[1]
            try:
                home = urlopen(f"http://127.0.0.1:{port}/").read().decode()
                self.assertIn("The Newsren", home)
                story = urlopen(
                    f"http://127.0.0.1:{port}/story/abc123abc123abcd?q=benchmark"
                ).read().decode()
                self.assertIn(LONG, story)
                self.assertIn("Chip report followup from the source", story)
                self.assertIn('href="/story/def456def456def4"', story)
                cross_source = urlopen(f"http://127.0.0.1:{port}/story/abc123abc123abcd?q=cost").read().decode()
                ask_region = cross_source.split('id="story-ask"')[1].split('id="story-explain"')[0]
                self.assertIn("A later clause mentions cost for this model in the source excerpt here.", ask_region)
                self.assertIn("SEC Press Releases", ask_region)
                payload = json.load(urlopen(f"http://127.0.0.1:{port}/api/stories"))
                self.assertEqual(payload["stories"][0]["category"], "finance")
                script = urlopen(f"http://127.0.0.1:{port}/static/reader.js").read().decode()
                self.assertIn("seenIds", script)
                try:
                    urlopen(f"http://127.0.0.1:{port}/story/not-an-id")
                    self.fail("expected 404")
                except Exception as exc:
                    self.assertEqual(exc.code, 404)
                    self.assertIn('href="/"', exc.read().decode())
                    exc.close()
            finally:
                httpd.shutdown()
                httpd.server_close()

    def test_post_refresh_uses_store(self):
        store = FakeStore()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(store))
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        port = httpd.server_address[1]
        try:
            urlopen(f"http://127.0.0.1:{port}/").read()
            self.assertEqual(store.calls, 0)
            payload = json.load(
                urlopen(Request(f"http://127.0.0.1:{port}/api/refresh", method="POST", data=b""))
            )
            self.assertEqual(store.calls, 1)
            self.assertEqual(payload["stories"][0]["id"], "abc123abc123abcd")
        finally:
            httpd.shutdown()
            httpd.server_close()

    def test_taken_port_exits(self):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            with self.assertRaises(SystemExit) as caught:
                with redirect_stderr(io.StringIO()) as err:
                    make_server(store, port=port)
            self.assertEqual(caught.exception.code, 1)
            self.assertIn(f"Port {port} is already in use", err.getvalue())
        sock.close()

    def test_background_refresh_clears_flag(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            done = threading.Event()

            def refresh(opener=None, now=None):
                done.set()
                return store.snapshot()

            store.refresh = refresh
            store.refreshing = True
            stop = threading.Event()
            start_background_refresh(store, interval_seconds=3600, stop_event=stop)
            self.assertTrue(done.wait(2))
            for _ in range(50):
                if not store.refreshing:
                    break
                time.sleep(0.01)
            self.assertFalse(store.refreshing)
            stop.set()

    def test_background_refresh_continues_after_error(self):
        with TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "cache.json")
            done = threading.Event()
            calls = {"n": 0}

            def refresh(opener=None, now=None):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise OSError("disk full")
                done.set()
                return store.snapshot()

            store.refresh = refresh
            stop = threading.Event()
            with redirect_stderr(io.StringIO()) as err:
                start_background_refresh(store, interval_seconds=0.01, stop_event=stop)
                self.assertTrue(done.wait(2))
            self.assertIn("disk full", err.getvalue())
            stop.set()


if __name__ == "__main__":
    unittest.main()
