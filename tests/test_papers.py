import io
import json
import unittest

from newsren import papers


XML = b'''<article article-type="research-article"><front><journal-meta><journal-title-group><journal-title>Example Education Journal</journal-title></journal-title-group></journal-meta><article-meta>
<article-id pub-id-type="pmcid">PMC1234567</article-id><article-id pub-id-type="doi">10.1234/education.1</article-id>
<title-group><article-title>AI tutoring in school mathematics</article-title></title-group>
<pub-date><year>2025</year><month>6</month><day>25</day></pub-date>
<abstract><p>Students used an AI tutor in a randomized trial.</p></abstract>
</article-meta></front><body>
<sec><title>Methods</title>
<p>We conducted a randomized controlled trial in a single high school in Turkey with 240 students in grades 9 and 10.</p>
<p>Classes were randomly assigned to three groups: a control group, a general AI assistant, and an AI tutor providing hints.</p></sec>
<sec><title>Results</title>
<p>During assisted practice, students using the general assistant scored 40% higher than the control group.</p>
<p>On the subsequent unassisted exam, the general assistant group scored 10% lower than the control group.</p></sec>
<sec><title>Discussion</title>
<p>Our study is limited to one school and one subject. Long-term retention and transfer to unfamiliar problems were not measured.</p>
<p>Future work should measure transfer to unfamiliar problems.</p></sec>
<sec><title>References</title><p>A different study measured transfer with 9000 students.</p></sec>
</body></article>'''


class Reply(io.BytesIO):
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class Transport:
    def __init__(self, bodies):
        self.bodies = list(bodies)
        self.urls = []
    def open(self, request, timeout):
        self.urls.append(request.full_url)
        return Reply(self.bodies.pop(0))


class PaperTests(unittest.TestCase):
    def parser(self, xml=XML):
        self.assertTrue(hasattr(papers, "parse_paper"))
        return papers.parse_paper(xml, "PMC1234567", "2026-10-26T12:00:00Z")

    def test_jats_metadata_and_only_article_paragraphs_are_preserved(self):
        paper = self.parser()
        self.assertEqual(paper["doi"], "10.1234/education.1")
        self.assertEqual(paper["publication_status"], "published_journal_article")
        self.assertEqual(paper["published_at"], "2025-06-25")
        self.assertEqual(paper["retrieved_at"], "2026-10-26T12:00:00Z")
        self.assertNotIn("9000", " ".join(row["text"] for row in paper["paragraphs"]))
        self.assertTrue(all(row["anchor"] for row in paper["paragraphs"]))

    def test_preprint_is_not_labelled_as_peer_reviewed(self):
        paper = self.parser(XML.replace(b'research-article', b'preprint'))
        self.assertEqual(paper["publication_status"], "preprint")
        self.assertFalse(paper["peer_review_verified"])

    def test_wrong_document_or_absent_body_does_not_become_full_text(self):
        self.assertTrue(hasattr(papers, "parse_paper"))
        with self.assertRaises(ValueError):
            papers.parse_paper(XML, "PMC9999999", "now")
        with self.assertRaises(ValueError):
            papers.parse_paper(XML.replace(b"<body>", b"<other>").replace(b"</body>", b"</other>"), "PMC1234567", "now")

    def test_doi_resolution_fetches_only_fixed_api_and_checks_identity(self):
        self.assertTrue(hasattr(papers, "PaperClient"))
        metadata = json.dumps({"resultList": {"result": [{"doi": "10.1234/education.1", "pmcid": "PMC1234567"}]}}).encode()
        transport = Transport([metadata, XML])
        paper = papers.PaperClient(opener=transport).fetch("https://doi.org/10.1234/education.1")
        self.assertEqual(paper["pmcid"], "PMC1234567")
        self.assertEqual(len(transport.urls), 2)
        self.assertTrue(all(url.startswith("https://www.ebi.ac.uk/europepmc/webservices/rest/") for url in transport.urls))
        self.assertTrue(transport.urls[-1].endswith("/PMC1234567/fullTextXML"))

    def test_arbitrary_urls_or_invalid_ids_are_rejected_before_network(self):
        self.assertTrue(hasattr(papers, "PaperClient"))
        transport = Transport([])
        for identifier in ("https://evil.invalid/paper.xml", "PMC123/../../secret", '10.1234/foo" OR *'):
            with self.assertRaises(ValueError):
                papers.PaperClient(opener=transport).fetch(identifier)
        self.assertEqual(transport.urls, [])

    def test_mismatched_doi_metadata_and_full_text_are_rejected(self):
        for metadata_doi, xml in (("10.1234/different", XML), ("10.1234/education.1", XML.replace(b"10.1234/education.1", b"10.1234/different"))):
            metadata = json.dumps({"resultList": {"result": [{"doi": metadata_doi, "pmcid": "PMC1234567"}]}}).encode()
            transport = Transport([metadata, xml])
            with self.assertRaises(ValueError):
                papers.PaperClient(opener=transport).fetch("10.1234/education.1")
            self.assertEqual(len(transport.urls), 1 if metadata_doi.endswith("different") else 2)

    def test_resolution_without_full_text_does_not_fetch_arbitrary_path(self):
        for pmcid in ("", "PMC123/../../secret"):
            metadata = json.dumps({"resultList": {"result": [{"doi": "10.1234/education.1", "pmcid": pmcid}]}}).encode()
            transport = Transport([metadata])
            with self.assertRaises(ValueError):
                papers.PaperClient(opener=transport).fetch("10.1234/education.1")
            self.assertEqual(len(transport.urls), 1)


if __name__ == "__main__":
    unittest.main()
