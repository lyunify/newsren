import unittest

from newsren.summary import build_summary


LONG = "This sentence is definitely long enough to qualify as a preferred summary sentence today."
ALSO = "Another preferred sentence follows with enough characters to pass the length window easily."


class SummaryTests(unittest.TestCase):
    def test_preferred_sentences_are_substrings(self):
        excerpt = f"{LONG} {ALSO}"
        built = build_summary("Short title", excerpt)
        self.assertEqual(built["summary_sentences"], [LONG, ALSO])
        self.assertFalse(built["summary_truncated"])
        for sentence in built["summary_sentences"]:
            self.assertIn(sentence, excerpt)

    def test_caps_at_three_preferred_sentences(self):
        third = "A third preferred sentence is also long enough to be kept in the summary output."
        fourth = "A fourth preferred sentence is long enough but must be left out of the summary."
        built = build_summary("Title", f"{LONG} {ALSO} {third} {fourth}")
        self.assertEqual(len(built["summary_sentences"]), 3)

    def test_short_excerpt_falls_back_without_adding_words(self):
        built = build_summary("Tiny", "Only a short excerpt")
        self.assertEqual(built["summary_sentences"], ["Only a short excerpt"])
        self.assertTrue(built["summary_truncated"])

    def test_empty_excerpt_has_no_summary(self):
        built = build_summary("Title only", "")
        self.assertEqual(built["summary_sentences"], [])
        self.assertFalse(built["summary_truncated"])

    def test_title_sentence_in_range_counts(self):
        title = "This headline itself is long enough to be one preferred summary sentence."
        built = build_summary(title, "")
        self.assertEqual(built["summary_sentences"], [title])
        self.assertIn(built["summary_sentences"][0], title)

    def test_excerpt_sentence_is_kept_ahead_of_a_long_title(self):
        title = "This headline itself is long enough to be one preferred summary sentence."
        built = build_summary(title, LONG)
        self.assertEqual(built["summary_sentences"], [LONG])

    def test_same_sentence_in_title_and_excerpt_appears_once(self):
        title = "This headline itself is long enough to be one preferred summary sentence."
        built = build_summary(title, title)
        self.assertEqual(built["summary_sentences"], [title])


if __name__ == "__main__":
    unittest.main()
