import unittest

from newsren.follow import change_quotes, unseen_matches


def story(story_id, title, summary):
    return {
        "id": story_id,
        "title": title,
        "summary_sentences": summary,
        "excerpt": "benchmark appears only in the excerpt and not the summary",
    }


class FollowTests(unittest.TestCase):
    def test_stopword_short_word_and_chinese_do_not_match(self):
        item = story("a1", "The ai benchmark landed", ["The ai benchmark landed in public"])
        self.assertEqual(unseen_matches("the and", [item], set()), [])
        self.assertEqual(unseen_matches("go", [item], set()), [])
        self.assertEqual(unseen_matches("半导体", [item], set()), [])

    def test_term_matches_summary_and_skips_seen(self):
        item = story("a1", "Lab result", ["An independent benchmark was published yesterday"])
        other = story("b2", "Other", ["An independent benchmark was published yesterday"])
        found = unseen_matches("benchmark", [item, other], {"a1"})
        self.assertEqual([row["id"] for row in found], ["b2"])

    def test_excerpt_only_word_does_not_match(self):
        item = story("a1", "Lab result", ["A short note"])
        self.assertEqual(unseen_matches("benchmark", [item], set()), [])

    def test_skips_later_restatement_of_the_same_story(self):
        older = story("old", "Apple iPhone display reports", ["Apple iPhone display reports continue today."])
        older["published_at"] = "2026-10-20T00:00:00Z"
        repeat = story("dup", "Apple iPhone display reports update", ["Apple iPhone display reports continue today."])
        repeat["published_at"] = "2026-10-25T00:00:00Z"
        newer = story("new", "Apple iPhone display cracks", ["Apple acknowledges iPhone display cracks."])
        newer["published_at"] = "2026-10-26T00:00:00Z"
        found = unseen_matches("iphone", [older, repeat, newer], set())
        self.assertEqual([row["id"] for row in found], ["old", "new"])

    def test_change_quotes_cap_at_three_and_skip_restatement(self):
        older = story(
            "old",
            "Apple iPhone display reports",
            [
                "Apple iPhone display reports continue today.",
                "Another display sentence is long enough for the first story.",
            ],
        )
        older["published_at"] = "2026-10-20T00:00:00Z"
        older["url"] = "https://example.com/old"
        older["source_name"] = "The Verge"
        repeat = story("dup", "Apple iPhone display reports update", ["Apple iPhone display reports continue today."])
        repeat["published_at"] = "2026-10-25T00:00:00Z"
        newer = story("new", "Apple iPhone display cracks", ["Apple acknowledges iPhone display cracks."])
        newer["published_at"] = "2026-10-26T00:00:00Z"
        newer["url"] = "https://example.com/new"
        newer["source_name"] = "Ars Technica"
        extra = story(
            "x3",
            "Apple iPhone display probe",
            ["A third new display sentence appears only in this later report."],
        )
        extra["published_at"] = "2026-10-27T00:00:00Z"
        quotes = change_quotes("iphone", [older, repeat, newer, extra], set())
        self.assertEqual(
            [row["sentence"] for row in quotes],
            [
                "Apple iPhone display reports continue today.",
                "Another display sentence is long enough for the first story.",
                "Apple acknowledges iPhone display cracks.",
            ],
        )
        self.assertEqual(quotes[0]["id"], "old")
        self.assertEqual(quotes[0]["url"], "https://example.com/old")
        self.assertEqual(quotes[2]["title"], "Apple iPhone display cracks")
        self.assertNotIn("dup", [row["id"] for row in quotes])


if __name__ == "__main__":
    unittest.main()
