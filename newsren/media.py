"""Publisher-supplied feed images, without fetching article pages."""

import re
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from newsren.text import strip_html

MEDIA_NS = "{http://search.yahoo.com/mrss/}"


def safe_image_url(value, base=""):
    if not isinstance(value, str) or not value or len(value) > 4096 or any(c.isspace() for c in value):
        return ""
    try:
        url = urljoin(base, value)
        parts = urlsplit(url)
        host = (parts.hostname or "").lower().rstrip(".")
        if (parts.scheme != "https" or parts.username is not None or parts.password is not None
                or not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host
                or not re.search(r"[a-z]", host) or parts.port not in (None, 443)
                # Browsers interpret numeric/hex final labels as IPv4 candidates.
                or re.fullmatch(r"(?:[0-9]+|0x[0-9a-f]+)", host.rsplit(".", 1)[-1])
                or host.endswith((".local", ".localhost", ".internal", ".lan", ".invalid", ".test"))):
            return ""
        return url
    except ValueError:
        return ""


def _dimension(value):
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def display_image_url(url):
    """Use BBC's verified image-size route; retain the feed URL as provenance."""
    url = safe_image_url(url)
    if not url:
        return ""
    parts = urlsplit(url)
    match = re.fullmatch(r"/ace/standard/([0-9]+)/cpsprodpb/(.+)", parts.path)
    if parts.hostname == "ichef.bbci.co.uk" and match and 32 < int(match[1]) < 1200:
        return parts._replace(path="/ace/standard/1200/cpsprodpb/" + match[2]).geturl()
    return url


def _too_small(attrs):
    return any(0 < _dimension(attrs.get(key)) <= 32 for key in ("width", "height"))


class _HTMLImages(HTMLParser):
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.images = []

    def handle_starttag(self, tag, attrs):
        if tag != "img":
            return
        attrs = dict(attrs)
        if _too_small(attrs):
            return
        for key in ("src", "data-src"):
            url = safe_image_url(attrs.get(key), self.base)
            if url:
                self.images.append({"image_url": url, "image_alt": strip_html(attrs.get("alt") or "")[:300],
                                    "image_credit": strip_html(attrs.get("data-portal-copyright") or "")[:200],
                                    "image_width": _dimension(attrs.get("width"))})
                break


def feed_image(node, article_url):
    candidates = []
    for element in node.iter():
        local = element.tag.rsplit("}", 1)[-1].lower()
        media = element.tag.startswith(MEDIA_NS)
        attrs = element.attrib
        mime = attrs.get("type", "").lower()
        medium = attrs.get("medium", "").lower()
        if media and local in {"content", "thumbnail"}:
            if medium not in {"", "image"} or (mime and not mime.startswith("image/")):
                continue
            priority = 3 if local == "content" else 1
        elif local in {"enclosure", "link"} and mime.startswith("image/") and (local == "enclosure" or attrs.get("rel") == "enclosure"):
            priority = 2
        else:
            continue
        if _too_small(attrs):
            continue
        url = safe_image_url(attrs.get("url") or attrs.get("href"), article_url)
        if not url or re.search(r"\.(?:mp4|webm|mov|m4v|mp3|m4a|wav|ogg)$", urlsplit(url).path, re.I):
            continue
        credit = next((strip_html("".join(child.itertext())) for child in element.iter() if child.tag == MEDIA_NS + "credit"), "")
        alt = next((strip_html("".join(child.itertext())) for child in element.iter() if child.tag in {MEDIA_NS + "description", MEDIA_NS + "title"}), "")
        width = _dimension(attrs.get("width"))
        candidates.append((priority, width, {"image_url": url, "image_alt": alt[:300], "image_credit": credit[:200], "image_width": width}))
    # XHTML Atom content and escaped HTML RSS/Atom bodies are both supported.
    parser = _HTMLImages(article_url)
    for child in list(node):
        local = child.tag.rsplit("}", 1)[-1].lower()
        if local not in {"encoded", "content", "description", "summary"} or child.tag.startswith(MEDIA_NS):
            continue
        for element in child.iter():
            if element.tag.rsplit("}", 1)[-1].lower() == "img":
                parser.handle_starttag("img", list(element.attrib.items()))
        parser.feed("".join(child.itertext()))
    candidates.extend((2, image["image_width"], image) for image in parser.images)
    if candidates:
        return max(candidates, key=lambda item: (item[0], item[1]))[2]
    return {"image_url": "", "image_alt": "", "image_credit": "", "image_width": 0}
