import unittest

from newsren.depth import cache_stats, impact_sentences, lesson_cloze, tracker_rows


def story(**overrides):
    base = {
        "id": "aaa111aaa111aaaa",
        "title": "Apple iPhone display reports",
        "url": "https://example.com/a",
        "source_name": "The Verge",
        "category": "technology",
        "published_at": "2026-10-26T00:00:00Z",
        "excerpt": "Apple acknowledges iPhone display cracks after reports.",
        "summary_sentences": ["Apple acknowledges iPhone display cracks after reports."],
    }
    base.update(overrides)
    return base


class DepthTests(unittest.TestCase):
    def test_lesson_cloze_blanks_a_title_word_in_a_source_sentence(self):
        found = lesson_cloze(story())
        self.assertEqual(found["answer"].lower(), "apple")
        self.assertIn("_____", found["prompt"])
        self.assertNotIn(found["answer"], found["prompt"])
        self.assertEqual(found["sentence"], "Apple acknowledges iPhone display cracks after reports.")

    def test_impact_quotes_only_source_sentences_with_effect_words(self):
        item = story(
            category="industry",
            summary_sentences=["Chip suppliers reported higher costs after the outage."],
        )
        other = story(
            id="bbb222bbb222bbbb",
            title="Later note",
            summary_sentences=["The company shipped phones last week."],
        )
        found = impact_sentences(item, [other])
        self.assertEqual(
            [row["sentence"] for row in found],
            ["Chip suppliers reported higher costs after the outage."],
        )
        self.assertEqual(found[0]["id"], "aaa111aaa111aaaa")

    def test_tracker_rows_label_finance_stories_from_source_words(self):
        filing = story(
            id="fin1fin1fin1fin1",
            category="finance",
            title="SEC enforcement action announced",
            summary_sentences=["The SEC announced an enforcement action today."],
            source_name="SEC Press Releases",
        )
        other = story(category="technology")
        plain = story(
            id="fin2fin2fin2fin2",
            category="finance",
            title="Board meeting notice",
            summary_sentences=["The board met this morning."],
        )
        found = tracker_rows([filing, other, plain])
        self.assertEqual([(row["id"], row["label"]) for row in found], [("fin1fin1fin1fin1", "enforcement")])

    def test_cache_stats_counts_sections_and_source_errors(self):
        snapshot = {
            "stories": [
                story(category="technology"),
                story(id="bbb222bbb222bbbb", category="finance"),
            ],
            "sources": [
                {"name": "The Verge", "last_error": ""},
                {"name": "EdSurge", "last_error": "timeout"},
            ],
        }
        found = cache_stats(snapshot)
        self.assertEqual(found["stories"], 2)
        self.assertEqual(found["by_category"]["technology"], 1)
        self.assertEqual(found["by_category"]["finance"], 1)
        self.assertEqual(found["sources_ok"], 1)
        self.assertEqual(found["sources_down"], 1)


if __name__ == "__main__":
    unittest.main()
