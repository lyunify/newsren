import unittest
from datetime import datetime, timezone

from newsren.text import (
    USER_AGENT,
    english_words,
    normalize_title,
    normalize_url,
    parse_date,
    split_sentences,
    story_id,
    strip_html,
)


class TextTests(unittest.TestCase):
    def test_user_agent(self):
        self.assertEqual(
            USER_AGENT,
            "NewsrenLocal/0.1 (student project; research use; admin@localhost)",
        )

    def test_tracking_params_share_one_id(self):
        clean = "https://Example.com/story/"
        tagged = "https://example.com/story?utm_source=rss&fbclid=abc&id=7"
        self.assertEqual(normalize_url(clean), "https://example.com/story")
        self.assertEqual(normalize_url(tagged), "https://example.com/story?id=7")
        self.assertEqual(story_id(clean), story_id("https://example.com/story?utm_medium=email"))
        self.assertEqual(len(story_id(clean)), 16)

    def test_title_punctuation_collapses(self):
        self.assertEqual(normalize_title("AI Model!"), normalize_title("AI Model"))
        self.assertNotEqual(
            normalize_title("New AI model launches"),
            normalize_title("New AI model launched"),
        )

    def test_strip_html_entities(self):
        self.assertEqual(strip_html("<b>A &amp; B</b>"), "A & B")

    def test_strip_html_separates_adjacent_tags(self):
        self.assertEqual(strip_html("<p>A</p><p>B</p>"), "A B")
        self.assertEqual(strip_html("<figcaption>Radeco</figcaption>The robot"), "Radeco The robot")

    def test_split_on_spec_punctuation(self):
        text = "First sentence is here. Second one? Third one! 第四句。 第五句？"
        self.assertEqual(
            split_sentences(text),
            ["First sentence is here.", "Second one?", "Third one!", "第四句。", "第五句？"],
        )

    def test_parse_rfc822_and_iso(self):
        rfc = parse_date("Mon, 26 Oct 2026 12:00:00 GMT")
        iso = parse_date("2026-10-26T12:00:00Z")
        self.assertEqual(rfc, iso)
        self.assertEqual(rfc.tzinfo, timezone.utc)
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date("not a date"))

    def test_english_words_keep_short_tokens(self):
        self.assertEqual(english_words("The AI models"), ["the", "ai", "models"])


if __name__ == "__main__":
    unittest.main()
