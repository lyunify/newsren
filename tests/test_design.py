import unittest
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen

from newsren.papers import PaperClient
from newsren.research import ResearchAgent
from newsren.research_pages import render_research_run
from newsren.store import Store
from tests.http_support import serve
from tests.test_papers import Transport, XML


class FragmentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = []
        self.fragments = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a" and attrs.get("href", "").startswith("#"):
            self.fragments.append(attrs["href"][1:])


class ReaderDesignTests(unittest.TestCase):
    def test_research_starts_with_answer_and_all_navigation_and_citations_resolve(self):
        agent = ResearchAgent(paper_client=PaperClient(opener=Transport([XML])))
        run = agent.run("Does AI improve learning?", [], paper_id="PMC1234567")
        html = render_research_run(run)
        self.assertLess(html.index('id="research-answer"'), html.index('id="education-study"'))
        parser = FragmentParser()
        parser.feed(html)
        self.assertTrue(set(parser.fragments) <= set(parser.ids))
        self.assertEqual(len(parser.ids), len(set(parser.ids)))
        self.assertIn('aria-label="In this research"', html)
        self.assertIn("Review: pending", html)

    def test_design_assets_are_local_and_explicitly_served(self):
        with TemporaryDirectory() as tmp:
            with serve(Store(Path(tmp) / "cache.json")) as base:
                for path, mime in (("design.css", "text/css"), ("interface.js", "text/javascript")):
                    with urlopen(base + "/static/" + path) as response:
                        self.assertEqual(response.headers.get_content_type(), mime)
                        self.assertEqual(response.read(), Path("static", path).read_bytes())


if __name__ == "__main__":
    unittest.main()
