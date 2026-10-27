import unittest

from newsren.ask import ask_stories, find_supporting_sentences


EXCERPT = "Models ship today. The lab published an independent benchmark. A later clause mentions cost."


class AskTests(unittest.TestCase):
    def test_hit_returns_source_sentence_in_original_order(self):
        found = find_supporting_sentences(
            "Chip report",
            EXCERPT,
            "independent benchmark cost",
        )
        self.assertEqual(
            found,
            [
                "The lab published an independent benchmark.",
                "A later clause mentions cost.",
            ],
        )
        for sentence in found:
            self.assertIn(sentence, EXCERPT)

    def test_whole_word_only(self):
        found = find_supporting_sentences("Chip report", "Models ship today.", "model")
        self.assertEqual(found, [])

    def test_stopwords_and_blank_return_empty(self):
        self.assertEqual(find_supporting_sentences("Title", EXCERPT, "the and"), [])
        self.assertEqual(find_supporting_sentences("Title", EXCERPT, "   "), [])

    def test_short_word_ai_still_matches_ask(self):
        found = find_supporting_sentences("Title", "The ai lab opened.", "ai")
        self.assertEqual(found, ["The ai lab opened."])

    def test_chinese_question_returns_empty(self):
        found = find_supporting_sentences("Title", EXCERPT, "半导体")
        self.assertEqual(found, [])

    def test_no_hit_returns_empty(self):
        self.assertEqual(find_supporting_sentences("Title", EXCERPT, "unicorn"), [])


class AskStoriesTests(unittest.TestCase):
    def test_keeps_current_story_first_and_labels_the_other_source(self):
        current = {
            "id": "aaa111aaa111aaaa",
            "title": "Chip report",
            "excerpt": "The lab published an independent benchmark.",
            "url": "https://example.com/a",
            "source_name": "The Verge",
        }
        other = {
            "id": "bbb222bbb222bbbb",
            "title": "Chip followup",
            "excerpt": "A later clause mentions cost.",
            "url": "https://example.com/b",
            "source_name": "Ars Technica",
        }
        found = ask_stories("benchmark cost", [current, other])
        self.assertEqual(
            found,
            [
                {
                    "sentence": "The lab published an independent benchmark.",
                    "id": "aaa111aaa111aaaa",
                    "title": "Chip report",
                    "url": "https://example.com/a",
                    "source_name": "The Verge",
                },
                {
                    "sentence": "A later clause mentions cost.",
                    "id": "bbb222bbb222bbbb",
                    "title": "Chip followup",
                    "url": "https://example.com/b",
                    "source_name": "Ars Technica",
                },
            ],
        )

    def test_caps_total_hits_and_skips_stories_without_a_hit(self):
        stories = []
        for index in range(7):
            stories.append(
                {
                    "id": f"{index:016x}",
                    "title": f"Story {index}",
                    "excerpt": f"An independent benchmark number {index} was published yesterday.",
                    "url": f"https://example.com/{index}",
                    "source_name": "The Verge",
                }
            )
        stories.append(
            {
                "id": "ffffffffffffffff",
                "title": "Unrelated",
                "excerpt": "No matching words here.",
                "url": "https://example.com/none",
                "source_name": "BBC Technology",
            }
        )
        found = ask_stories("benchmark", stories)
        self.assertEqual(len(found), 6)
        self.assertEqual([item["id"] for item in found], [f"{index:016x}" for index in range(6)])
        self.assertNotIn("ffffffffffffffff", [item["id"] for item in found])

    def test_chinese_or_blank_question_returns_empty(self):
        item = {
            "id": "aaa111aaa111aaaa",
            "title": "Chip report",
            "excerpt": EXCERPT,
            "url": "https://example.com/a",
            "source_name": "The Verge",
        }
        self.assertEqual(ask_stories("半导体", [item]), [])
        self.assertEqual(ask_stories("   ", [item]), [])


if __name__ == "__main__":
    unittest.main()
