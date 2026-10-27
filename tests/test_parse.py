import unittest

from newsren.parse import parse_feed
from newsren.sources import APPROVED_SOURCES

SOURCE = {"name": "The Verge", "category": "technology", "url": "https://example.test/feed"}
LONG = "This description is long enough to become one preferred summary sentence for the card."
ALSO = "Another description is also long enough to stay a preferred sentence if content is short."


class SourceTests(unittest.TestCase):
    def test_catalog_matches_spec(self):
        self.assertEqual(
            [(item["name"], item["category"]) for item in APPROVED_SOURCES],
            [
                ("The Verge", "technology"),
                ("Ars Technica", "technology"),
                ("MIT Technology Review", "technology"),
                ("BBC Technology", "technology"),
                ("IEEE Spectrum", "technology"),
                ("EdSurge", "education"),
                ("BBC Education", "education"),
                ("Supply Chain Dive", "industry"),
                ("BBC Business", "industry"),
                ("Federal Reserve", "finance"),
                ("SEC Press Releases", "finance"),
            ],
        )
        joined = " ".join(item["url"] for item in APPROVED_SOURCES)
        self.assertNotIn("browse-edgar", joined)
        self.assertIn("https://www.federalreserve.gov/feeds/press_all.xml", joined)
        self.assertIn("https://www.sec.gov/news/pressreleases.rss", joined)


class ParseTests(unittest.TestCase):
    def test_rss_item(self):
        xml = f"""<?xml version="1.0"?>
        <rss version="2.0"><channel><item>
          <title>Chip report</title>
          <link>https://example.com/a?utm_source=rss</link>
          <description><![CDATA[<p>{LONG}</p>]]></description>
          <pubDate>Mon, 26 Oct 2026 12:00:00 GMT</pubDate>
        </item></channel></rss>""".encode()
        rows = parse_feed(xml, SOURCE, "2026-10-26T13:00:00+00:00")
        self.assertEqual(rows[0]["title"], "Chip report")
        self.assertEqual(rows[0]["url"], "https://example.com/a?utm_source=rss")
        self.assertEqual(rows[0]["excerpt"], LONG)
        self.assertEqual(rows[0]["summary_sentences"], [LONG])
        self.assertEqual(rows[0]["category"], "technology")
        self.assertEqual(rows[0]["published_at"], "Mon, 26 Oct 2026 12:00:00 GMT")

    def test_atom_feed(self):
        xml = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom"><entry>
          <title>Atom chip</title>
          <link rel="alternate" href="https://example.com/atom"/>
          <summary>Atom summary text.</summary>
          <published>2026-10-26T12:00:00Z</published>
        </entry></feed>"""
        rows = parse_feed(xml, SOURCE, "2026-10-26T13:00:00+00:00")
        self.assertEqual(rows[0]["title"], "Atom chip")
        self.assertEqual(rows[0]["url"], "https://example.com/atom")
        self.assertEqual(rows[0]["excerpt"], "Atom summary text.")

    def test_bom_and_html_entity(self):
        xml = """<?xml version="1.0"?>
        <rss><channel><item>
          <title>A &amp; B</title>
          <link>https://example.com/b</link>
          <description><b>A &amp; B</b> shipped.</description>
        </item></channel></rss>""".encode()
        rows = parse_feed(b"\xef\xbb\xbf" + xml, SOURCE, "2026-10-26T13:00:00+00:00")
        self.assertEqual(rows[0]["title"], "A & B")
        self.assertEqual(rows[0]["excerpt"], "A & B shipped.")

    def test_short_content_falls_back_to_description(self):
        xml = f"""<?xml version="1.0"?>
        <rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>
          <title>Chip report</title>
          <link>https://example.com/short</link>
          <content:encoded><![CDATA[<figcaption>Tesla</figcaption>]]></content:encoded>
          <description><![CDATA[<p>{LONG}</p>]]></description>
        </item></channel></rss>""".encode()
        rows = parse_feed(xml, SOURCE, "2026-10-26T13:00:00+00:00")
        self.assertEqual(rows[0]["excerpt"], LONG)

    def test_long_content_stays_ahead_of_description(self):
        xml = f"""<?xml version="1.0"?>
        <rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>
          <title>Chip report</title>
          <link>https://example.com/long</link>
          <content:encoded><![CDATA[<p>{LONG}</p>]]></content:encoded>
          <description><![CDATA[<p>{ALSO}</p>]]></description>
        </item></channel></rss>""".encode()
        rows = parse_feed(xml, SOURCE, "2026-10-26T13:00:00+00:00")
        self.assertEqual(rows[0]["excerpt"], LONG)

    def test_media_content_does_not_replace_the_article(self):
        caption = "The Cerberus quadruped robot sold by Radeco is a modified version of the robot and this caption is long enough."
        xml = f"""<?xml version="1.0"?>
        <rss xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:media="http://search.yahoo.com/mrss/">
        <channel><item>
          <title>Chip report</title>
          <link>https://example.com/media</link>
          <description>Short desc.</description>
          <content:encoded><![CDATA[<p>{LONG}</p>]]></content:encoded>
          <media:content url="https://example.com/a.jpg">
            <media:credit>Radeco</media:credit>
            <media:text>{caption}</media:text>
          </media:content>
        </item></channel></rss>""".encode()
        rows = parse_feed(xml, SOURCE, "2026-10-26T13:00:00+00:00")
        self.assertEqual(rows[0]["excerpt"], LONG)
        self.assertNotIn("RadecoThe", rows[0]["excerpt"])

    def test_skips_item_without_link(self):
        xml = b"""<rss><channel><item><title>No link</title></item></channel></rss>"""
        self.assertEqual(parse_feed(xml, SOURCE, "2026-10-26T13:00:00+00:00"), [])


if __name__ == "__main__":
    unittest.main()
