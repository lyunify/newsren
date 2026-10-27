import unittest
from io import BytesIO

from newsren.fetch import fetch_source
from newsren.text import USER_AGENT

SOURCE = {"name": "The Verge", "category": "technology", "url": "https://example.test/feed"}
LONG = "This item description is long enough to count as a preferred summary sentence."


class FakeResponse:
    def __init__(self, body):
        self.body = body
        self.stream = BytesIO(body)

    def read(self, size=-1):
        return self.stream.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeOpener:
    def __init__(self, body=b"", error=None, capture=None):
        self.body = body
        self.error = error
        self.capture = capture

    def open(self, request, timeout=None):
        if self.capture is not None:
            self.capture["timeout"] = timeout
            self.capture["header"] = request.header_items()
        if self.error:
            raise self.error
        return FakeResponse(self.body)


def item(index, published):
    return f"""<item>
      <title>Story {index}</title>
      <link>https://example.com/{index}</link>
      <description>{LONG}</description>
      <pubDate>{published}</pubDate>
    </item>"""


class FetchTests(unittest.TestCase):
    def test_sends_user_agent_and_timeout(self):
        capture = {}
        xml = f"<rss><channel>{item(1, 'Mon, 26 Oct 2026 12:00:00 GMT')}</channel></rss>".encode()
        rows, error = fetch_source(SOURCE, "2026-10-26T13:00:00+00:00", FakeOpener(xml, capture=capture))
        self.assertEqual(error, "")
        self.assertEqual(rows[0]["title"], "Story 1")
        self.assertEqual(capture["timeout"], 12)
        self.assertIn(("User-agent", USER_AGENT), capture["header"])

    def test_http_error_returns_message(self):
        rows, error = fetch_source(
            SOURCE,
            "2026-10-26T13:00:00+00:00",
            FakeOpener(error=RuntimeError("HTTP Error 500")),
        )
        self.assertEqual(rows, [])
        self.assertEqual(error, "RuntimeError: HTTP Error 500")

    def test_keeps_newest_twenty(self):
        pieces = []
        for index in range(21):
            day = 21 - index
            pieces.append(item(index, f"{day:02d} Oct 2026 00:00:00 GMT"))
        pieces.append(item(99, ""))
        xml = ("<rss><channel>" + "".join(pieces) + "</channel></rss>").encode()
        rows, error = fetch_source(SOURCE, "2026-10-26T13:00:00+00:00", FakeOpener(xml))
        self.assertEqual(error, "")
        self.assertEqual(len(rows), 20)
        self.assertEqual(rows[0]["url"], "https://example.com/0")
        self.assertNotIn("https://example.com/99", [row["url"] for row in rows])


if __name__ == "__main__":
    unittest.main()
