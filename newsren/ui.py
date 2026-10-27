"""Shared editorial shell; presentation only, no retrieval or model calls."""

from datetime import datetime
from email.utils import parsedate_to_datetime
from html import escape


def masthead(active="news"):
    links = [("news", "/", "The edition"), ("research", "/research", "Research"),
             ("review", "/review", "Review desk")]
    nav = "".join(f'<a href="{url}"' + (' aria-current="page"' if key == active else '')
                  + f'>{label}</a>' for key, url, label in links)
    return f'''<header class="mast"><div class="wrap mast-inner">
<a class="brand" href="/" aria-label="The Newsren home">The Newsren<span class="brand-mark" aria-hidden="true">.</span></a>
<nav class="site-nav" aria-label="Main navigation">{nav}</nav>
<span class="mast-note">A little news. A deeper understanding.</span>
</div></header>'''


def footer():
    return '''<footer class="site-footer wrap"><a class="brand" href="/">The Newsren<span class="brand-mark">.</span></a>
<p>Read widely. Think clearly.</p><a href="/research">Follow the evidence <span aria-hidden="true">↗</span></a></footer>'''


def contents(items, label="In this story"):
    links = "".join(f'<a href="#{escape(key, quote=True)}"><span>{i:02}</span>{escape(text)}</a>'
                    for i, (key, text) in enumerate(items, 1))
    return f'<aside class="contents-rail"><nav class="contents" aria-label="{escape(label, quote=True)}"><p class="eyebrow">{escape(label)}</p>{links}<a class="contents-back" href="#main-content">Back to top ↑</a></nav></aside>'


def display_date(value):
    if not value:
        return "Date unavailable"
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return value
    return date.strftime("%d %b %Y").lstrip("0")
