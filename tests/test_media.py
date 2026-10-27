import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from newsren.cache import save_cache
from newsren.pages import reader_catalog, render_home, render_story
from newsren.parse import parse_feed
from newsren.store import Store
from tests.test_pages import snapshot, story

SOURCE = {"name": "The Verge", "category": "technology", "url": "https://example.com/feed"}


def feed(body):
    return f'''<rss xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><item>
    <title>A science report</title><link>https://example.com/news/science</link>
    <description>A source description with enough words to form a complete summary sentence.</description>{body}
    </item></channel></rss>'''.encode()


class PublisherImageTests(unittest.TestCase):
    def test_bbc_thumbnail_uses_same_photo_at_readable_resolution_with_fallback(self):
        original = "https://ichef.bbci.co.uk/ace/standard/240/cpsprodpb/896f/live/photo.jpg"
        item = story(image_url=original, image_width=240)
        for html in (render_home(snapshot([item])), render_story(item)):
            self.assertIn('src="' + original.replace('/240/', '/1200/') + '"', html)
            self.assertIn('data-image-fallback="' + original + '"', html)
        # Other publishers and already larger images must retain their URLs.
        for url in (original.replace('ichef.bbci.co.uk', 'cdn.example.com'), original.replace('/240/', '/1536/')):
            self.assertIn('src="' + url + '"', render_story(story(image_url=url)))

    def test_media_full_image_precedes_thumbnail_and_credit_does_not_become_excerpt(self):
        xml = feed('''<media:thumbnail url="https://cdn.example.com/thumb.jpg" width="240"/>
        <media:content medium="image" url="https://cdn.example.com/full.jpg" width="1200" height="800">
        <media:credit>Jane Doe / Example</media:credit><media:description>A research lab.</media:description></media:content>''')
        row = parse_feed(xml, SOURCE, "2026-10-27T00:00:00Z")[0]
        self.assertEqual(row.get("image_url"), "https://cdn.example.com/full.jpg")
        self.assertEqual(row["image_credit"], "Jane Doe / Example")
        self.assertEqual(row["image_width"], 1200)
        self.assertNotIn("Jane Doe", row["excerpt"])

    def test_html_image_resolves_relative_url_and_retains_alt_and_publisher_credit(self):
        xml = feed('''<content:encoded><![CDATA[<figure><img src="/photos/lab.jpg" alt="A research lab" data-portal-copyright="Image: Example"/></figure><p>The original source text remains the evidence for this report.</p>]]></content:encoded>''')
        row = parse_feed(xml, SOURCE, "now")[0]
        self.assertEqual(row.get("image_url"), "https://example.com/photos/lab.jpg")
        self.assertEqual(row["image_alt"], "A research lab")
        self.assertEqual(row["image_credit"], "Image: Example")
        self.assertNotIn("A research lab", row["excerpt"])

    def test_atom_enclosure_and_image_enclosure_supported(self):
        rss = parse_feed(feed('<enclosure url="https://cdn.example.com/photo.png" type="image/png"/>'), SOURCE, "now")[0]
        self.assertEqual(rss.get("image_url"), "https://cdn.example.com/photo.png")
        atom = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Report</title><link href="https://example.com/a"/><link rel="enclosure" type="image/webp" href="https://cdn.example.com/a.webp"/><summary>Source text.</summary></entry></feed>'''
        self.assertEqual(parse_feed(atom, SOURCE, "now")[0].get("image_url"), "https://cdn.example.com/a.webp")

    def test_non_images_tiny_trackers_and_unsafe_urls_are_not_rendered(self):
        bad = ["javascript:alert(1)", "data:image/svg+xml,x", "https://localhost/x.jpg", "https://127.0.0.1/x.jpg", "https://127.1/x.jpg", "https://user:secret@cdn.example.com/x.jpg",
               "https://0x7f.0.0.1/x.jpg", "https://0xa.0.0.1/x.jpg", "https://0xc0.0xa8.1.1/x.jpg", "https://127.0.0.0x1/x.jpg"]
        for url in bad:
            with self.subTest(url=url):
                row = parse_feed(feed(f'<media:content medium="image" url="{url}"/>'), SOURCE, "now")[0]
                self.assertFalse(row.get("image_url"))
        row = parse_feed(feed('''<enclosure url="https://cdn.example.com/a.mp3" type="audio/mpeg"/>
        <content:encoded><![CDATA[<img src="https://cdn.example.com/pixel.gif" width="1" height="1"/>]]></content:encoded>'''), SOURCE, "now")[0]
        self.assertFalse(row.get("image_url"))

    def test_malformed_article_link_does_not_discard_valid_feed_items(self):
        xml = b'''<rss><channel><item><title>Bad</title><link>https://[malformed</link></item>
        <item><title>Valid report</title><link>https://example.com/valid</link></item></channel></rss>'''
        rows = parse_feed(xml, SOURCE, "now")
        self.assertEqual([row["title"] for row in rows], ["Valid report"])

    def test_video_media_without_a_type_does_not_displace_an_article_photo(self):
        row = parse_feed(feed('''<media:content url="https://cdn.example.com/clip.mp4"/>
        <content:encoded><![CDATA[<img src="https://cdn.example.com/photo.jpg"/>]]></content:encoded>'''), SOURCE, "now")[0]
        self.assertEqual(row.get("image_url"), "https://cdn.example.com/photo.jpg")

    def test_images_are_escaped_and_source_linked_with_text_fallback(self):
        item = story(image_url="https://cdn.example.com/a.jpg", image_alt='A lab "room"', image_credit="Jane Doe")
        for html in (render_home(snapshot([item])), render_story(item)):
            self.assertIn('src="https://cdn.example.com/a.jpg"', html)
            self.assertIn('referrerpolicy="no-referrer"', html)
            self.assertIn("Jane Doe", html)
            self.assertNotIn('alt="A lab "room""', html)
        html = render_home(snapshot([story()]))
        self.assertNotIn('<img ', html)
        self.assertIn("Chip report", html)
        malicious = render_home(snapshot([story(image_url="javascript:alert(1)")]))
        self.assertNotIn('<img ', malicious)

    def test_image_metadata_survives_cache_without_creating_a_content_update(self):
        item = story(image_url="https://cdn.example.com/a.jpg", image_credit="Jane Doe", image_width=1200)
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "cache.json"
            save_cache(path, {"stories": [item], "sources": {}})
            saved = Store(path).get(item["id"])
            self.assertEqual(saved["image_url"], item["image_url"])
        before = story()
        self.assertEqual(Store._content_key(before), Store._content_key(item))
        self.assertEqual(reader_catalog([before])[0]["followKey"], reader_catalog([item])[0]["followKey"])

    def test_three_column_edition_uses_a_photo_lead_without_duplicating_cards(self):
        items = [story(id=f"{i:016x}", title=f"Report {i}", url=f"https://example.com/{i}") for i in range(9)]
        items[2].update(image_url="https://cdn.example.com/lead.jpg", image_width=1200)
        html = render_home(snapshot(items))
        self.assertIn('data-edition-column="lead"', html)
        lead = html.split('data-edition-column="lead"', 1)[1].split('</section>', 1)[0]
        self.assertIn("Report 2", lead)
        self.assertIn("lead.jpg", lead)
        self.assertEqual(html.count('data-edition-order='), len(items))


if __name__ == "__main__":
    unittest.main()
