import json
import unittest
from pathlib import Path

from newsren.pages import (
    ASK_NOTE,
    BRIEFING_NOTE,
    CLAIM_HEADING,
    EMAIL_NOTE,
    EMPTY_FEED,
    FINANCE_NOTICE,
    FOLLOW_EMPTY,
    GLOSSARY_HEADING,
    HOME_DEK,
    IMPACT_HEADING,
    INSPECT_HEADING,
    LESSON_HEADING,
    OTHER_NOTE,
    RELATED_EMPTY,
    RELATED_NOTE,
    STATS_HEADING,
    TRACKER_HEADING,
    UNREPEATED_NONE,
    UNREPEATED_NOTE,
    UNREPEATED_NO_RELATED,
    UNCERTAINTY_HEADING,
    LOADING,
    NO_EXCERPT,
    NO_SUPPORT,
    SOURCE_DOWN,
    STUDENT_NOTE,
    SUMMARY_NOTE,
    TRUNCATED_NOTE,
    render_home,
    render_not_found,
    render_story,
)
from newsren.text import STOPWORDS


def story(**overrides):
    base = {
        "id": "abc123abc123abcd",
        "title": "Chip report",
        "url": "https://example.com/a",
        "source_name": "The Verge",
        "category": "technology",
        "published_at": "2026-10-26T12:00:00Z",
        "retrieved_at": "2026-10-26T13:00:00+00:00",
        "excerpt": "An independent benchmark was published.",
        "summary_sentences": ["An independent benchmark was published."],
        "summary_truncated": False,
    }
    base.update(overrides)
    return base


def snapshot(stories, sources=None, refreshing=False):
    if sources is None:
        sources = [
            {
                "name": "The Verge",
                "category": "technology",
                "url": "https://example.test/feed",
                "last_success_at": "2026-10-26T13:00:00+00:00",
                "last_error": "",
                "last_error_at": "",
            }
        ]
    return {"stories": stories, "sources": sources, "refreshing": refreshing}


class PageTests(unittest.TestCase):
    def test_home_card_and_dek(self):
        html = render_home(snapshot([story()]))
        self.assertIn("The Newsren", html)
        self.assertIn(HOME_DEK, html)
        self.assertIn("Chip report", html)
        self.assertIn("https://example.com/a", html)
        self.assertIn("2026-10-26T13:00:00+00:00", html)
        self.assertIn(SUMMARY_NOTE, html)
        self.assertIn(FINANCE_NOTICE, html)
        self.assertNotIn("Inter", html)
        self.assertNotIn("Roboto", html)
        self.assertNotIn("Arial", html)
        self.assertNotIn("买入", html)
        self.assertNotIn("目标价", html)

    def test_card_shows_only_two_sentences(self):
        sentences = [
            "This first summary sentence is long enough to be shown on the card itself.",
            "This second summary sentence is also long enough to be shown on the card.",
            "This third summary sentence stays in the data but not in the card text.",
        ]
        html = render_home(snapshot([story(summary_sentences=sentences)]))
        card = html.split('id="story-list"', 1)[1].split('id="following"', 1)[0]
        self.assertIn(sentences[0], card)
        self.assertIn(sentences[1], card)
        self.assertNotIn(sentences[2], card)
        self.assertIn(sentences[2], html)

    def test_source_error_empty_and_loading(self):
        sources = [
            {
                "name": "The Verge",
                "category": "technology",
                "url": "https://example.test/feed",
                "last_success_at": "",
                "last_error": "RuntimeError: HTTP Error 500",
                "last_error_at": "2026-10-26T13:00:00+00:00",
            }
        ]
        error_html = render_home(snapshot([story()], sources=sources))
        self.assertIn("The Verge", error_html)
        self.assertIn(SOURCE_DOWN, error_html)
        empty = render_home(snapshot([], sources=sources, refreshing=False))
        self.assertIn(EMPTY_FEED, empty)
        self.assertIn('id="refresh"', empty)
        loading = render_home(snapshot([], refreshing=True))
        self.assertIn(LOADING, loading)
        self.assertNotIn('id="refresh"', loading)

    def test_truncated_and_missing_excerpt(self):
        truncated = render_home(snapshot([story(summary_sentences=["Only a short excerpt"], summary_truncated=True, excerpt="Only a short excerpt")]))
        self.assertIn("Only a short excerpt…", truncated)
        self.assertIn(TRUNCATED_NOTE, truncated)
        missing = render_home(snapshot([story(title="Bare", excerpt="", summary_sentences=[], summary_truncated=False)]))
        self.assertIn(NO_EXCERPT, missing)
        self.assertIn("https://example.com/a", missing)

    def test_script_payload_cannot_break_out(self):
        hostile = story(title="</script><script>alert(1)</script>")
        html = render_home(snapshot([hostile]))
        self.assertNotIn("</script><script>alert(1)", html)
        data = html.split('id="newsren-data" type="application/json">', 1)[1].split("</script>", 1)[0]
        parsed = json.loads(data)
        self.assertEqual(parsed["stories"][0]["title"], "</script><script>alert(1)</script>")
        self.assertTrue(STOPWORDS.issubset(set(parsed["stopwords"])))
        self.assertEqual(parsed["followEmpty"], FOLLOW_EMPTY)
        self.assertIn("materialUpdate", parsed["stories"][0])
        self.assertIn("changeSentences", parsed["stories"][0])

    def test_home_payload_marks_restatement_as_not_material(self):
        older = story(
            id="olderolderolder1",
            title="Apple iPhone display reports",
            published_at="2026-10-20T00:00:00Z",
            summary_sentences=["Apple iPhone display reports continue today."],
        )
        repeat = story(
            id="dupdupdupdupdup1",
            title="Apple iPhone display reports update",
            published_at="2026-10-25T00:00:00Z",
            summary_sentences=["Apple iPhone display reports continue today."],
        )
        html = render_home(snapshot([older, repeat]))
        data = html.split('id="newsren-data" type="application/json">', 1)[1].split("</script>", 1)[0]
        parsed = json.loads(data)
        by_id = {row["id"]: row for row in parsed["stories"]}
        self.assertTrue(by_id["olderolderolder1"]["materialUpdate"])
        self.assertFalse(by_id["dupdupdupdupdup1"]["materialUpdate"])
        self.assertEqual(
            by_id["olderolderolder1"]["changeSentences"],
            ["Apple iPhone display reports continue today."],
        )
        self.assertEqual(by_id["dupdupdupdupdup1"]["changeSentences"], [])

    def test_finance_story_sections_and_ask(self):
        item = story(category="finance", source_name="Federal Reserve")
        html = render_story(item, "benchmark", ["An independent benchmark was published."])
        self.assertLess(html.index("Chip report"), html.index(FINANCE_NOTICE))
        self.assertLess(html.index(FINANCE_NOTICE), html.index("Ask this story"))
        self.assertLess(html.index("Ask this story"), html.index("Explain for"))
        self.assertLess(html.index("Explain for"), html.index("Follow this question"))
        self.assertEqual(html.count(FINANCE_NOTICE), 2)
        self.assertIn(ASK_NOTE, html)
        self.assertIn("An independent benchmark was published.", html)
        self.assertIn(STUDENT_NOTE, html)
        self.assertIn("What does this story claim?", html)
        self.assertIn("What evidence does the source give?", html)
        self.assertIn("What does this summary not say?", html)
        self.assertIn("What is the original source", html)
        self.assertIn("Is the time explicit", html)
        self.assertIn("Which parts are only this source's account and have not been repeated by another source", html)
        self.assertNotIn("买入", html)
        educator = html.split('data-audience="educator"', 1)[1].split("data-audience=\"professional\"", 1)[0]
        professional = html.split('data-audience="professional"', 1)[1]
        self.assertIn("An independent benchmark was published.", educator)
        self.assertIn("An independent benchmark was published.", professional)

    def test_ask_miss_and_blank_question(self):
        miss = render_story(story(), "unicorn", [])
        self.assertIn(NO_SUPPORT, miss)
        self.assertNotIn(ASK_NOTE, miss)
        blank = render_story(story(), "   ", None)
        self.assertNotIn(NO_SUPPORT, blank)

    def test_ask_labels_a_hit_from_a_related_story(self):
        item = story()
        other = story(
            id="bbb222bbb222bbbb",
            title="Chip followup",
            url="https://example.com/b",
            source_name="Ars Technica",
        )
        html = render_story(
            item,
            "cost",
            [
                {
                    "sentence": "A later clause mentions cost.",
                    "id": "bbb222bbb222bbbb",
                    "title": "Chip followup",
                    "url": "https://example.com/b",
                    "source_name": "Ars Technica",
                }
            ],
            related=[other],
        )
        self.assertIn(ASK_NOTE, html)
        self.assertIn("<blockquote><p>A later clause mentions cost.</p>", html)
        self.assertIn("Ars Technica", html)
        self.assertIn('href="/story/bbb222bbb222bbbb"', html)
        self.assertIn("https://example.com/b", html)
        self.assertNotIn("{'sentence':", html)
        self.assertNotIn(NO_SUPPORT, html)

    def test_related_stories_are_listed_after_follow(self):
        item = story()
        older = story(
            id="olderolderolder1",
            title="Earlier chip",
            source_name="Ars Technica",
            category="technology",
            published_at="2026-10-20T00:00:00Z",
        )
        newer = story(
            id="newernewernewer1",
            title="Later chip",
            source_name="BBC Technology",
            category="industry",
            published_at="",
        )
        html = render_story(item, related=[older, newer])
        related = html.split('id="story-related"', 1)[1]
        self.assertLess(html.index("Follow this question"), html.index("Connected stories"))
        self.assertIn(RELATED_NOTE, html)
        self.assertLess(related.index("Earlier chip"), related.index("Chip report"))
        self.assertLess(related.index("Chip report"), related.index("Later chip"))
        self.assertIn('href="/story/olderolderolder1"', related)
        self.assertIn("This story", related)
        self.assertNotIn('href="/story/abc123abc123abcd"', related)
        self.assertIn("Ars Technica", html)
        self.assertIn("2026-10-20T00:00:00Z", html)
        self.assertIn("Industry", html)
        self.assertIn("The source did not provide a publication time.", html)
        empty = render_story(item)
        self.assertIn(RELATED_EMPTY, empty)
        self.assertNotIn(RELATED_NOTE, empty)

    def test_what_is_new_uses_earlier_related_stories_only(self):
        item = story(
            summary_sentences=[
                "Apple acknowledges iPhone display cracks.",
                "Apple iPhone display reports today.",
            ]
        )
        older = story(
            id="olderolderolder1",
            title="Earlier chip",
            published_at="2026-10-20T00:00:00Z",
            summary_sentences=["Apple iPhone display reports continue today."],
        )
        later = story(
            id="newernewernewer1",
            title="Later chip",
            published_at="2026-10-27T00:00:00Z",
            summary_sentences=["Apple acknowledges iPhone display cracks in a later note."],
        )
        html = render_story(item, related=[older, later])
        related = html.split('id="story-related"', 1)[1]
        self.assertIn("What is new in this story", related)
        self.assertIn("Apple acknowledges iPhone display cracks.", related.split("What is new in this story", 1)[1])
        self.assertNotIn(
            "Apple iPhone display reports today.",
            related.split("What is new in this story", 1)[1],
        )
        newest = story(published_at="2026-10-20T00:00:00Z")
        later_only = render_story(newest, related=[later])
        self.assertIn("There are no earlier related stories to compare.", later_only)

    def test_related_title_cannot_break_the_page(self):
        html = render_story(story(), related=[story(id="badbadbadbadbad1", title="</script><script>alert(1)</script>")])
        self.assertNotIn("</script><script>alert(1)", html)

    def test_professional_panel_quotes_unrepeated_sentences(self):
        item = story(
            summary_sentences=[
                "Apple acknowledges iPhone display cracks.",
                "Apple iPhone display reports today.",
            ]
        )
        other = story(
            id="bbb222bbb222bbbb",
            title="Apple iPhone display reports",
            summary_sentences=["Apple iPhone display reports continue today."],
        )
        html = render_story(item, related=[other])
        self.assertIn("Which parts are only this source's account and have not been repeated by another source", html)
        self.assertIn(UNREPEATED_NOTE, html)
        self.assertIn("Apple acknowledges iPhone display cracks.", html)
        none = render_story(
            story(summary_sentences=["Apple iPhone display reports today."]),
            related=[other],
        )
        self.assertIn(UNREPEATED_NONE, none)
        empty = render_story(item)
        self.assertIn(UNREPEATED_NO_RELATED, empty)

    def test_story_page_has_named_regions(self):
        html = render_story(story())
        order = [
            "story-header",
            "story-summary",
            "story-ask",
            "story-explain",
            "story-follow",
            "story-related",
            "story-inspect",
            "story-lesson",
            "story-impact",
        ]
        places = [html.index(f'id="{name}"') for name in order]
        self.assertEqual(places, sorted(places))
        self.assertIn('id="ask-form"', html)
        self.assertIn('id="question"', html)
        self.assertIn('id="follow"', html)

    def test_inspect_quotes_sources_uncertainty_and_other_sections(self):
        item = story(
            title="Apple iPhone display reports",
            excerpt="Apple may acknowledge iPhone display cracks after reports.",
            summary_sentences=["Apple may acknowledge iPhone display cracks after reports."],
        )
        industry = story(
            id="ind1ind1ind1ind1",
            title="Apple iPhone supply note",
            url="https://example.com/i",
            source_name="Supply Chain Dive",
            category="industry",
            summary_sentences=["Apple iPhone suppliers reported screen replacements."],
        )
        html = render_story(item, related=[industry])
        inspect = html.split('id="story-inspect"', 1)[1]
        self.assertLess(html.index("Connected stories"), html.index(INSPECT_HEADING))
        self.assertIn(UNCERTAINTY_HEADING, inspect)
        self.assertIn("Apple may acknowledge iPhone display cracks after reports.", inspect)
        self.assertIn("The Verge", inspect)
        self.assertIn("https://example.com/a", inspect)
        self.assertIn("Supply Chain Dive", inspect)
        self.assertIn(OTHER_NOTE, inspect)
        self.assertIn("Apple iPhone supply note", inspect)
        self.assertIn("Apple iPhone suppliers reported screen replacements.", inspect)
        self.assertIn(GLOSSARY_HEADING, html)
        self.assertIn("iphone", html)

    def test_finance_inspect_labels_claim_words(self):
        item = story(
            category="finance",
            source_name="Federal Reserve",
            excerpt="The bank reported a two-decade backtest.",
            summary_sentences=["The bank reported a two-decade backtest."],
        )
        html = render_story(item)
        inspect = html.split('id="story-inspect"', 1)[1]
        self.assertIn(CLAIM_HEADING, inspect)
        self.assertIn("backtest", inspect)
        self.assertIn("The bank reported a two-decade backtest.", inspect)
        tech = render_story(story(summary_sentences=["Staff ate lunch today after the meeting ended."]))
        self.assertNotIn(CLAIM_HEADING, tech.split('id="story-inspect"', 1)[1])

    def test_home_has_finance_tracker_and_cache_stats(self):
        filing = story(
            id="fin1fin1fin1fin1",
            category="finance",
            source_name="SEC Press Releases",
            title="SEC enforcement action announced",
            summary_sentences=["The SEC announced an enforcement action today."],
        )
        html = render_home(snapshot([story(), filing]))
        self.assertIn(TRACKER_HEADING, html)
        self.assertIn("enforcement", html)
        self.assertIn("SEC enforcement action announced", html)
        self.assertIn(STATS_HEADING, html)
        self.assertIn("2 stories", html)
        self.assertIn(EMAIL_NOTE, html)

    def test_story_has_lesson_cloze_and_impact_quotes(self):
        item = story(
            title="Apple iPhone display reports",
            excerpt="Apple acknowledges iPhone display cracks after reports.",
            summary_sentences=[
                "Apple acknowledges iPhone display cracks after reports.",
                "Chip suppliers reported higher costs after the outage.",
            ],
        )
        html = render_story(item)
        self.assertIn(LESSON_HEADING, html)
        self.assertIn("_____", html)
        self.assertIn(IMPACT_HEADING, html)
        self.assertIn("Chip suppliers reported higher costs after the outage.", html)

    def test_not_found_links_home(self):
        html = render_not_found()
        self.assertIn('href="/"', html)

    def test_reader_script_uses_length_and_seen_ids(self):
        script = Path("static/reader.js").read_text(encoding="utf-8")
        self.assertIn("word.length > 3", script)
        self.assertIn("seenIds", script)
        self.assertIn("materialUpdate", script)
        self.assertIn("changeSentences", script)
        self.assertIn("What changed", script)
        self.assertIn("Briefing", script)
        self.assertIn(BRIEFING_NOTE, script)
        self.assertIn("mailto:", script)
        self.assertIn("Copy briefing", script)
        self.assertIn("Email briefing", script)
        self.assertNotIn("Inter", script)


if __name__ == "__main__":
    unittest.main()
