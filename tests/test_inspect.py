import unittest

from newsren.inspect import (
    claim_labels,
    glossary_entries,
    independent_sources,
    other_section_stories,
    uncertainty_sentences,
)


def story(**overrides):
    base = {
        "id": "aaa111aaa111aaaa",
        "title": "Apple iPhone display reports",
        "url": "https://example.com/a",
        "source_name": "The Verge",
        "category": "technology",
        "excerpt": "Apple may acknowledge iPhone display cracks after reports.",
        "summary_sentences": ["Apple may acknowledge iPhone display cracks after reports."],
    }
    base.update(overrides)
    return base


class InspectTests(unittest.TestCase):
    def test_uncertainty_quotes_hedge_sentences_only(self):
        item = story(
            title="Apple iPhone display reports",
            excerpt="Apple may acknowledge iPhone display cracks after reports. The company shipped phones last week.",
        )
        self.assertEqual(
            uncertainty_sentences(item),
            ["Apple may acknowledge iPhone display cracks after reports."],
        )

    def test_independent_sources_dedupes_same_outlet(self):
        item = story()
        other = story(
            id="bbb222bbb222bbbb",
            title="Apple iPhone display cracks",
            url="https://example.com/b",
            source_name="Ars Technica",
            category="industry",
        )
        repeat = story(
            id="ccc333ccc333cccc",
            url="https://example.com/c",
            source_name="The Verge",
        )
        found = independent_sources(item, [other, repeat])
        self.assertEqual(
            [(row["source_name"], row["url"]) for row in found],
            [
                ("The Verge", "https://example.com/a"),
                ("Ars Technica", "https://example.com/b"),
            ],
        )

    def test_other_section_stories_skip_same_section(self):
        item = story()
        industry = story(
            id="ind1ind1ind1ind1",
            title="Apple iPhone supply note",
            url="https://example.com/i",
            source_name="Supply Chain Dive",
            category="industry",
            summary_sentences=["Apple iPhone suppliers reported screen replacements."],
        )
        same = story(
            id="tec1tec1tec1tec1",
            title="Apple iPhone software note",
            category="technology",
        )
        found = other_section_stories(item, [industry, same])
        self.assertEqual([row["id"] for row in found], ["ind1ind1ind1ind1"])

    def test_claim_labels_mark_source_words_only(self):
        item = story(
            category="finance",
            excerpt="The bank reported a two-decade backtest. Guidance was unchanged. Staff ate lunch.",
            summary_sentences=[
                "The bank reported a two-decade backtest.",
                "Guidance was unchanged.",
                "Staff ate lunch.",
            ],
        )
        self.assertEqual(
            claim_labels(item),
            [
                {"sentence": "The bank reported a two-decade backtest.", "label": "backtest"},
                {"sentence": "Guidance was unchanged.", "label": "guidance"},
            ],
        )

    def test_glossary_uses_title_words_and_source_sentences(self):
        item = story(
            title="Apple iPhone display reports",
            excerpt="Apple acknowledges iPhone display cracks after reports.",
            summary_sentences=["Apple acknowledges iPhone display cracks after reports."],
        )
        found = glossary_entries(item)
        self.assertIn(
            {"word": "iphone", "sentence": "Apple acknowledges iPhone display cracks after reports."},
            found,
        )
        self.assertTrue(all(entry["word"] in entry["sentence"].lower() for entry in found))
        self.assertLessEqual(len(found), 5)


if __name__ == "__main__":
    unittest.main()
