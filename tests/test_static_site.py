import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory

from newsren.research import ResearchAgent
from tests.test_pages import snapshot, story
from tests.test_research import evidence_story


class LocalLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        self.urls.extend(value for name, value in attrs if name in {'href', 'src', 'action'} and value.startswith('/'))


class StaticSiteTests(unittest.TestCase):
    def test_export_excludes_presentation_and_removes_legacy_download(self):
        from unittest.mock import patch
        from newsren import static_site
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / 'site'
            root.mkdir()
            (root / 'presentation.pdf').write_bytes(b'old public presentation')
            private = Path(tmp) / 'private.pdf'
            private.write_bytes(b'private local presentation')
            with patch.object(static_site, 'PRESENTATION', private, create=True):
                static_site.export_site(snapshot([story()]), [], root, '/newsren')
            self.assertFalse((root / 'presentation.pdf').exists())
            self.assertEqual(private.read_bytes(), b'private local presentation')
            for file in root.rglob('*.html'):
                self.assertNotIn('presentation.pdf', file.read_text())
                self.assertNotIn('Five-minute guide', file.read_text())

    def test_subpath_export_resolves_all_internal_links_and_retains_citations(self):
        from newsren.static_site import export_site
        item = story()
        run = ResearchAgent().run('Acme Orion revenue', [evidence_story()])
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_site(snapshot([item]), [run], root, '/newsren')
            self.assertTrue((root / 'static/reader.js').is_file())
            for file in root.rglob('*.html'):
                html = file.read_text()
                self.assertNotIn('method="post"', html)
                self.assertIn('Static demo', html)
                links = LocalLinks()
                links.feed(html)
                for url in links.urls:
                    self.assertTrue(url.startswith('/newsren/'), (file, url))
                    path = root / url.split('?', 1)[0].split('#', 1)[0].removeprefix('/newsren/')
                    self.assertTrue(path.is_file() or (path / 'index.html').is_file(), (file, url))
            saved = json.loads((root / f'api/research/{run["id"]}.json').read_text())
            self.assertEqual(saved['evidence'], run['evidence'])
            self.assertEqual(saved['review']['status'], 'pending')
            reader = (root / f'story/{item["id"]}/index.html').read_text()
            self.assertIn('static-ask-data', reader)
            self.assertIn('/newsren/static/demo.js', reader)

    def test_export_never_fetches_or_copies_runtime_files_and_rejects_bad_paths(self):
        from newsren.static_site import export_site
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_site(snapshot([story()]), [], root, '')
            self.assertFalse((root / 'data').exists())
            self.assertTrue((root / '.nojekyll').is_file())
            for base in ('https://example.com', '/../escape', '/bad?x=1'):
                with self.assertRaises(ValueError):
                    export_site(snapshot([]), [], root, base)


if __name__ == '__main__':
    unittest.main()
