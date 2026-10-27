import unittest

from newsren.related import (
    change_sentences,
    material_update,
    new_sentences,
    related_stories,
    timeline_stories,
    unrepeated_sentences,
)


def story(story_id, title, published=""):
    return {
        "id": story_id,
        "title": title,
        "published_at": published,
        "source_name": "Example",
        "category": "technology",
    }


class RelatedTests(unittest.TestCase):
    def test_two_shared_title_words_match_and_one_does_not(self):
        current = story("a", "Apple iPhone pencil support arrives", "2026-10-26T00:00:00Z")
        other = story("b", "Apple acknowledges iPhone display issue", "2026-10-25T00:00:00Z")
        single = story("c", "Benchmark funding round closes", "2026-10-24T00:00:00Z")
        lone = story("d", "Benchmark model launches quietly today", "2026-10-23T00:00:00Z")
        found = related_stories(current, [current, other, single, lone])
        self.assertEqual([item["id"] for item in found], ["b"])

    def test_common_title_word_does_not_count(self):
        rows = [
            story(str(index), f"Federal {name} notice published", f"2026-10-2{index}T00:00:00Z")
            for index, name in enumerate(["alpha", "bravo", "charlie", "delta", "echo"])
        ]
        self.assertEqual(related_stories(rows[0], rows), [])

    def test_orders_oldest_first_and_puts_missing_dates_last(self):
        current = story("now", "Gardner bancshares enforcement update", "2026-10-26T00:00:00Z")
        newer = story("new", "Gardner bancshares case continues", "2026-10-27T00:00:00Z")
        older = story("old", "Gardner bancshares review opens", "2026-10-20T00:00:00Z")
        undated = story("none", "Gardner bancshares filing noted", "")
        found = related_stories(current, [newer, current, undated, older])
        self.assertEqual([item["id"] for item in found], ["old", "new", "none"])

    def test_caps_at_five_most_recent_then_keeps_time_order(self):
        current = story(
            "now",
            "alpha beta gamma delta epsilon zeta theta iota kappa lambda micron nebula",
            "2026-10-10T00:00:00Z",
        )
        pairs = [
            "alpha beta",
            "gamma delta",
            "epsilon zeta",
            "theta iota",
            "kappa lambda",
            "micron nebula",
        ]
        others = [
            story(str(day), f"{pair} outside story", f"2026-10-{day:02d}T00:00:00Z")
            for day, pair in enumerate(pairs, start=1)
        ]
        found = related_stories(current, [current, *others])
        self.assertEqual([item["id"] for item in found], ["2", "3", "4", "5", "6"])

    def test_chinese_title_has_no_related_stories(self):
        current = story("a", "半导体出口新规", "2026-10-26T00:00:00Z")
        other = story("b", "半导体出口细则", "2026-10-25T00:00:00Z")
        self.assertEqual(related_stories(current, [current, other]), [])


class TimelineTests(unittest.TestCase):
    def test_includes_current_story_oldest_first(self):
        current = story("now", "Gardner bancshares enforcement update", "2026-10-26T00:00:00Z")
        older = story("old", "Gardner bancshares review opens", "2026-10-20T00:00:00Z")
        later = story("new", "Gardner bancshares case continues", "2026-10-27T00:00:00Z")
        undated = story("none", "Gardner bancshares filing noted", "")
        found = timeline_stories(current, [later, older, undated])
        self.assertEqual(
            [(row["story"]["id"], row["is_current"]) for row in found],
            [("old", False), ("now", True), ("new", False), ("none", False)],
        )

    def test_does_not_duplicate_current_if_it_is_in_related(self):
        current = story("now", "Gardner bancshares enforcement update", "2026-10-26T00:00:00Z")
        found = timeline_stories(current, [current])
        self.assertEqual([(row["story"]["id"], row["is_current"]) for row in found], [("now", True)])


class NewSentenceTests(unittest.TestCase):
    def test_compares_only_against_earlier_related_stories(self):
        current = story("now", "Apple iPhone display update", "2026-10-26T00:00:00Z")
        current["summary_sentences"] = [
            "Apple acknowledges iPhone display cracks.",
            "Apple iPhone display reports today.",
        ]
        older = story("old", "Apple iPhone display reports", "2026-10-20T00:00:00Z")
        older["summary_sentences"] = ["Apple iPhone display reports continue today."]
        later = story("new", "Apple iPhone display cracks confirmed", "2026-10-27T00:00:00Z")
        later["summary_sentences"] = ["Apple acknowledges iPhone display cracks in a later note."]
        found = new_sentences(current, [older, later])
        self.assertEqual(found, ["Apple acknowledges iPhone display cracks."])

    def test_no_earlier_related_means_no_new_sentences(self):
        current = story("now", "Apple iPhone display update", "2026-10-20T00:00:00Z")
        current["summary_sentences"] = ["Apple acknowledges iPhone display cracks."]
        later = story("new", "Apple iPhone display cracks confirmed", "2026-10-27T00:00:00Z")
        later["summary_sentences"] = ["Apple acknowledges iPhone display cracks in a later note."]
        self.assertEqual(new_sentences(current, [later]), [])


class MaterialUpdateTests(unittest.TestCase):
    def test_first_or_standalone_story_is_material(self):
        first = story("old", "Apple iPhone display reports", "2026-10-20T00:00:00Z")
        first["summary_sentences"] = ["Apple iPhone display reports continue today."]
        later = story("new", "Apple iPhone display cracks", "2026-10-26T00:00:00Z")
        later["summary_sentences"] = ["Apple acknowledges iPhone display cracks."]
        lone = story("solo", "Benchmark funding round closes", "2026-10-26T00:00:00Z")
        lone["summary_sentences"] = ["An independent benchmark was published."]
        self.assertTrue(material_update(first, [first, later]))
        self.assertTrue(material_update(lone, [first, later, lone]))

    def test_later_restatement_is_not_material_but_new_word_is(self):
        older = story("old", "Apple iPhone display reports", "2026-10-20T00:00:00Z")
        older["summary_sentences"] = ["Apple iPhone display reports continue today."]
        repeat = story("dup", "Apple iPhone display reports update", "2026-10-25T00:00:00Z")
        repeat["summary_sentences"] = ["Apple iPhone display reports continue today."]
        newer = story("new", "Apple iPhone display cracks", "2026-10-26T00:00:00Z")
        newer["summary_sentences"] = ["Apple acknowledges iPhone display cracks."]
        catalog = [older, repeat, newer]
        self.assertFalse(material_update(repeat, catalog))
        self.assertTrue(material_update(newer, catalog))


class ChangeSentenceTests(unittest.TestCase):
    def test_first_story_uses_its_summary_sentences(self):
        first = story("old", "Apple iPhone display reports", "2026-10-20T00:00:00Z")
        first["summary_sentences"] = ["Apple iPhone display reports continue today."]
        later = story("new", "Apple iPhone display cracks", "2026-10-26T00:00:00Z")
        later["summary_sentences"] = ["Apple acknowledges iPhone display cracks."]
        self.assertEqual(
            change_sentences(first, [first, later]),
            ["Apple iPhone display reports continue today."],
        )

    def test_later_story_keeps_only_new_sentences(self):
        older = story("old", "Apple iPhone display reports", "2026-10-20T00:00:00Z")
        older["summary_sentences"] = ["Apple iPhone display reports continue today."]
        newer = story("new", "Apple iPhone display cracks", "2026-10-26T00:00:00Z")
        newer["summary_sentences"] = [
            "Apple iPhone display reports continue today.",
            "Apple acknowledges iPhone display cracks.",
        ]
        self.assertEqual(
            change_sentences(newer, [older, newer]),
            ["Apple acknowledges iPhone display cracks."],
        )


class UnrepeatedTests(unittest.TestCase):
    def test_empty_related_returns_no_sentences(self):
        current = story("a", "Apple iPhone pencil support arrives")
        current["summary_sentences"] = ["Apple has just released pencil support for the iPhone Duo."]
        self.assertEqual(unrepeated_sentences(current, []), [])

    def test_keeps_source_sentence_when_a_word_is_absent_elsewhere(self):
        current = story("a", "Apple iPhone display issue")
        current["summary_sentences"] = [
            "Apple acknowledges iPhone display cracks.",
            "Apple iPhone display reports today.",
        ]
        other = story("b", "Apple iPhone display reports")
        other["summary_sentences"] = ["Apple iPhone display reports continue today."]
        found = unrepeated_sentences(current, [other])
        self.assertEqual(found, ["Apple acknowledges iPhone display cracks."])
        self.assertIn(found[0], current["summary_sentences"])

    def test_all_shared_words_mean_nothing_is_unrepeated(self):
        current = story("a", "Apple iPhone display reports")
        current["summary_sentences"] = ["Apple iPhone display reports today."]
        other = story("b", "Apple iPhone display reports")
        other["summary_sentences"] = ["Apple iPhone display reports continue today."]
        self.assertEqual(unrepeated_sentences(current, [other]), [])


if __name__ == "__main__":
    unittest.main()
