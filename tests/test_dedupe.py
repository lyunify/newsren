import unittest

from newsren.dedupe import dedupe_stories
from newsren.text import story_id


def story(url, title, category="technology", published="", source="The Verge"):
    return {
        "id": story_id(url),
        "title": title,
        "url": url,
        "source_name": source,
        "category": category,
        "published_at": published,
        "retrieved_at": "2026-10-26T00:00:00+00:00",
        "excerpt": title,
        "summary_sentences": [title] if len(title) >= 40 else [],
        "summary_truncated": False,
    }


class DedupeTests(unittest.TestCase):
    def test_utm_link_collapses_to_one(self):
        first = story("https://example.com/a", "One headline about a chip report today")
        second = story("https://example.com/a?utm_source=rss", "One headline about a chip report today")
        kept = dedupe_stories([first, second])
        self.assertEqual(len(kept), 1)

    def test_punctuation_title_collapses_and_word_change_does_not(self):
        bang = story("https://example.com/1", "AI Model!", published="2026-10-26T00:00:00Z")
        plain = story("https://example.com/2", "AI Model", published="2026-10-25T00:00:00Z")
        launches = story("https://example.com/3", "New AI model launches")
        launched = story("https://example.com/4", "New AI model launched")
        kept = dedupe_stories([bang, plain, launches, launched])
        titles = sorted(item["title"] for item in kept)
        self.assertEqual(titles, ["AI Model!", "New AI model launched", "New AI model launches"])

    def test_newer_published_story_wins(self):
        older = story("https://example.com/old", "AI Model", published="Mon, 25 Oct 2026 00:00:00 GMT")
        newer = story("https://example.com/new", "AI Model!", published="2026-10-26T00:00:00Z")
        kept = dedupe_stories([older, newer])
        self.assertEqual(kept[0]["url"], "https://example.com/new")

    def test_missing_dates_keep_the_first_story(self):
        first = story("https://example.com/1", "AI Model")
        second = story("https://example.com/2", "AI Model!")
        kept = dedupe_stories([first, second])
        self.assertEqual(kept[0]["url"], "https://example.com/1")

    def test_same_title_in_another_category_stays(self):
        tech = story("https://example.com/t", "AI Model", category="technology")
        edu = story("https://example.com/e", "AI Model", category="education")
        self.assertEqual(len(dedupe_stories([tech, edu])), 2)


if __name__ == "__main__":
    unittest.main()
