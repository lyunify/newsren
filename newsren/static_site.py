"""Export a public, read-only demo. No network, credentials or database access."""

import argparse
import json
import re
import shutil
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from newsren.pages import json_for_script, render_home, render_not_found, render_story
from newsren.related import related_stories
from newsren.research_pages import render_research_index, render_research_run
from newsren.text import STOPWORDS

ASSETS = Path(__file__).resolve().parent.parent / 'static'


def export_site(snapshot, runs, output, base_path='/newsren'):
    if base_path and not re.fullmatch(r'(?:/[A-Za-z0-9_-]+)+/?', base_path):
        raise ValueError('Use an absolute site path, for example /newsren, or an empty root path.')
    base = base_path.rstrip('/')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    # Remove the obsolete generated download when rebuilding an earlier export.
    (output / 'presentation.pdf').unlink(missing_ok=True)
    stories = snapshot['stories']
    for item in stories:
        if not re.fullmatch(r'[0-9a-f]{16}', item['id']):
            raise ValueError('Invalid exported story id')
    for run in runs:
        if not re.fullmatch(r'[0-9a-f]{32}', run['id']):
            raise ValueError('Invalid exported research id')
    demo_link = '/research/' + runs[0]['id'] if runs else '/research'

    def route(url):
        parts = urlsplit(url)
        path = parts.path
        if path.startswith('/api/research/'):
            path += '.json'
        elif path != '/' and not Path(path).suffix:
            path += '/'
        return urlunsplit(('', '', base + path, parts.query, parts.fragment))

    def page(html, ask_data=None):
        # Remove every backend POST form, including the review controls.
        def form_note(match):
            research = 'action="/research"' in match[0]
            if research:
                return ('<section class="research-compose demo-panel"><p class="eyebrow">Explore the saved example</p>'
                        '<h2>AI in education, with evidence.</h2><p>Read the saved answer, study passages, '
                        'limitations and review status. Creating new research requires the local Python app.</p>'
                        f'<a class="demo-link" href="{demo_link}">Open the education research note ↗</a></section>')
            return '<p class="notice">This is a saved review record. Review decisions can only be recorded in the local Python app.</p>'
        html = re.sub(r'<form\b(?=[^>]*method="post")[\s\S]*?</form>', form_note, html)
        html = re.sub(r'<button\b[^>]*id="refresh"[^>]*>[\s\S]*?</button>',
                      '<span class="muted">Saved news snapshot</span>', html)
        html = re.sub(r'\b(href|src|action)="(/[^\"]*)"',
                      lambda m: f'{m[1]}="{route(m[2])}"', html)
        html = html.replace('</head>', f'<meta name="newsren-base" content="{base}">\n</head>')
        notice = ('<aside class="demo-banner wrap" aria-label="Demo information"><strong>Static demo</strong>'
                  ' · Saved news and research. Reading, filters and browser-local follows work here. '
                  'New research, feed refresh and review writes need the local app. '
                  '<a href="https://github.com/lyunify/newsren">Project &amp; setup ↗</a></aside>')
        html = html.replace('</header>', '</header>' + notice, 1)
        extra = ''
        if ask_data is not None:
            extra += '<script type="application/json" id="static-ask-data">' + json_for_script(ask_data) + '</script>'
        extra += f'<script src="{base}/static/demo.js" defer></script>'
        return html.replace('</body>', extra + '\n</body>')

    def write(path, html, ask_data=None):
        file = output / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(page(html, ask_data), encoding='utf-8')

    write('index.html', render_home({**snapshot, 'refreshing': False}))
    for item in stories:
        related = related_stories(item, stories)
        write(f'story/{item["id"]}/index.html', render_story(item, related=related),
              {'stories': [item, *related], 'stopwords': sorted(STOPWORDS)})
    write('research/index.html', render_research_index(runs))
    write('review/index.html', render_research_index(runs, review=True))
    for run in runs:
        write(f'research/{run["id"]}/index.html', render_research_run(run))
        file = output / f'api/research/{run["id"]}.json'
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')
    write('404.html', render_not_found())
    for asset in ('design.css', 'reader.js', 'interface.js', 'demo.js'):
        (output / 'static').mkdir(exist_ok=True)
        shutil.copyfile(ASSETS / asset, output / 'static' / asset)
    (output / '.nojekyll').touch()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=Path('demo/news.json'))
    parser.add_argument('--research', type=Path, default=Path('demo/research.json'))
    parser.add_argument('--output', type=Path, default=Path('_site'))
    parser.add_argument('--base-path', default='/newsren')
    args = parser.parse_args()
    export_site(json.loads(args.input.read_text()), json.loads(args.research.read_text()), args.output, args.base_path)
    print('Exported static demo to', args.output)


if __name__ == '__main__':
    main()
