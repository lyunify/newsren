import unittest

from newsren.ask import find_supporting_sentences
from newsren.follow import unseen_matches
from newsren.related import material_update, related_stories
from newsren.text import split_sentences
from newsren.pages import render_home
from newsren.parse import parse_feed
import json


def article(key, title, sentence, day):
    return {
        "id": key, "title": title, "excerpt": sentence,
        "summary_sentences": [sentence], "category": "finance",
        "url": "https://example.org/" + key, "source_name": "Example",
        "published_at": f"2026-10-{day:02d}T00:00:00Z",
    }


class CompletionRegressions(unittest.TestCase):
    def test_abbreviations_do_not_cut_off_date_or_country(self):
        text = "The pause ends Nov. 9, after the U.S. and China finish talks. A second sentence follows."
        self.assertEqual(split_sentences(text), [
            "The pause ends Nov. 9, after the U.S. and China finish talks.",
            "A second sentence follows.",
        ])

    def test_identical_title_and_excerpt_quote_appears_once(self):
        sentence = "Acme Bank reports revenue of 100 million dollars."
        self.assertEqual(find_supporting_sentences(sentence, sentence, "revenue"), [sentence])

    def test_numeric_only_change_survives_follow_filter(self):
        old = article("old", "Acme Bank earnings released", "Acme Bank reports revenue of 100 million dollars.", 1)
        new = article("new", "Acme Bank earnings updated", "Acme Bank reports revenue of 200 million dollars.", 2)
        self.assertTrue(material_update(new, [old, new]))
        self.assertEqual([s["id"] for s in unseen_matches("Acme earnings", [old, new], {"old"})], ["new"])

    def test_filler_word_does_not_become_material_update(self):
        old = article("old", "Acme Bank earnings released", "Acme Bank reports revenue of 100 million dollars.", 1)
        new = article("new", "Acme Bank earnings updated", "Acme Bank reports total revenue of 100 million dollars.", 2)
        self.assertFalse(material_update(new, [old, new]))

    def test_positive_to_negative_amount_is_a_change(self):
        old = article("old", "Acme Bank earnings released", "Acme Bank reports earnings of 100 million dollars.", 1)
        new = article("new", "Acme Bank earnings updated", "Acme Bank reports earnings of -100 million dollars.", 2)
        self.assertTrue(material_update(new, [old, new]))

    def test_negation_is_a_material_change(self):
        old = article("old", "Acme Orion benchmark released", "Acme Orion can pass the benchmark.", 1)
        new = article("new", "Acme Orion benchmark updated", "Acme Orion cannot pass the benchmark.", 2)
        self.assertTrue(material_update(new, [old, new]))
        new["summary_sentences"] = ["Acme Orion can not pass the benchmark."]
        self.assertTrue(material_update(new, [old, new]))

    def test_numeric_values_swapping_between_metrics_is_a_change(self):
        old = article("old", "Acme Bank earnings", "Acme revenue was 100 million and costs were 200 million.", 1)
        new = article("new", "Acme Bank earnings updated", "Acme revenue was 200 million and costs were 100 million.", 2)
        self.assertTrue(material_update(new, [old, new]))

    def test_removing_a_contracted_negative_is_a_change(self):
        for apostrophe in ("'", "’"):
            old = article("old", "Acme Orion benchmark", f"Acme Orion isn{apostrophe}t able to pass the benchmark.", 1)
            new = article("new", "Acme Orion benchmark updated", "Acme Orion is able to pass the benchmark.", 2)
            self.assertTrue(material_update(new, [old, new]))

    def test_generic_small_business_words_do_not_connect_events(self):
        a = article("a", "Federal Reserve Board announces termination of enforcement actions with Gardner Bancshares, Inc. and Small Business Bank", "Gardner enforcement ends.", 1)
        b = article("b", "SEC Small Business Advisory Committee to Discuss IPO Modernization and Regulation Crowdfunding", "Committee discusses crowdfunding.", 2)
        self.assertEqual(related_stories(a, [a, b]), [])

    def test_ai_and_first_do_not_connect_school_opinion_to_biosecurity_lab(self):
        a = article("a", "Pause AI in Schools. But Not Before You Do This First.", "An opinion about AI in schools.", 1)
        b = article("b", "UK to invest £100m in world first AI Biosecurity Lab", "A new biosecurity laboratory.", 2)
        self.assertEqual(related_stories(a, [a, b]), [])

    def test_high_frequency_entity_stays_connected(self):
        rows = [article(str(i), f"Apple iPhone update {i}", "Apple iPhone report.", i + 1) for i in range(6)]
        self.assertEqual(len(related_stories(rows[-1], rows)), 5)

    def test_short_topic_ai_can_be_followed(self):
        a = article("a", "AI benchmark published", "The AI benchmark measured reasoning.", 1)
        self.assertEqual([s["id"] for s in unseen_matches("AI", [a], set())], ["a"])

    def test_follow_identity_changes_when_same_url_content_changes(self):
        old = article("same", "Acme Bank earnings", "Acme Bank revenue was 100 million dollars.", 1)
        new = dict(old, excerpt="Acme Bank revenue was 200 million dollars.", summary_sentences=["Acme Bank revenue was 200 million dollars."])
        keys = []
        for story in (old, new):
            html = render_home({"stories": [story], "sources": []})
            payload = json.loads(html.split('id="newsren-data" type="application/json">')[1].split('</script>')[0])
            keys.append(payload["stories"][0].get("followKey"))
        self.assertTrue(keys[0])
        self.assertNotEqual(keys[0], keys[1])

    def test_feed_cannot_supply_a_javascript_source_link(self):
        xml = b'<rss><channel><item><title>Bad URL</title><link>javascript:alert(1)</link></item></channel></rss>'
        self.assertEqual(parse_feed(xml, {"name": "Example", "category": "technology"}, "2026-10-01"), [])


if __name__ == "__main__":
    unittest.main()
