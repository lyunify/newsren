import xml.etree.ElementTree as ET
from urllib.parse import urlsplit

from newsren.summary import build_summary
from newsren.media import feed_image
from newsren.text import story_id, strip_html


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(node, name: str) -> str:
    for child in list(node):
        if _local(child.tag) == name:
            return "".join(child.itertext()).strip()
    return ""


def _ns(tag: str) -> str:
    if tag.startswith("{"):
        return tag[1:].split("}", 1)[0]
    return ""


def _excerpt(node) -> str:
    content = ""
    description = ""
    for child in list(node):
        name = _local(child.tag)
        text = "".join(child.itertext()).strip()
        if name == "encoded" or (name == "content" and _ns(child.tag) != "http://search.yahoo.com/mrss/"):
            if text:
                content = text
        elif name in {"description", "summary"} and text:
            description = text
    content_text = strip_html(content)
    description_text = strip_html(description)
    if len(content_text) >= 40:
        chosen = content_text
    elif len(description_text) > len(content_text):
        chosen = description_text
    else:
        chosen = content_text or description_text
    return chosen[:1200]


def _link(node) -> str:
    plain = _child_text(node, "link")
    if plain and not plain.startswith("<"):
        return plain
    for child in list(node):
        if _local(child.tag) != "link":
            continue
        href = child.attrib.get("href", "").strip()
        rel = child.attrib.get("rel", "alternate")
        if href and rel in {"alternate", ""}:
            return href
    for child in list(node):
        if _local(child.tag) == "link" and child.attrib.get("href"):
            return child.attrib["href"].strip()
    return ""


def _entries(root):
    kind = _local(root.tag)
    if kind in {"rss", "rdf"}:
        channel = next((child for child in list(root) if _local(child.tag) == "channel"), root)
        return [child for child in list(channel) if _local(child.tag) == "item"]
    if kind == "feed":
        return [child for child in list(root) if _local(child.tag) == "entry"]
    raise ValueError(f"unrecognized feed: {kind}")


def parse_feed(xml_bytes: bytes, source: dict, retrieved_at: str) -> list[dict]:
    payload = xml_bytes.lstrip(b"\xef\xbb\xbf")
    root = ET.fromstring(payload)
    stories = []
    for node in _entries(root):
        url = _link(node)
        try:
            parts = urlsplit(url)
        except ValueError:
            continue
        if not url or parts.scheme not in {"http", "https"} or not parts.netloc:
            continue
        title = strip_html(_child_text(node, "title"))
        excerpt = _excerpt(node)
        published = _child_text(node, "pubdate") or _child_text(node, "published") or _child_text(node, "updated")
        summary = build_summary(title, excerpt)
        image = feed_image(node, url)
        stories.append(
            {
                "id": story_id(url),
                "title": title,
                "url": url,
                "source_name": source["name"],
                "category": source["category"],
                "published_at": published,
                "retrieved_at": retrieved_at,
                "excerpt": excerpt,
                "summary_sentences": summary["summary_sentences"],
                "summary_truncated": summary["summary_truncated"],
                **image,
                "image_source_url": source.get("url", "") if image["image_url"] else "",
                "image_retrieved_at": retrieved_at if image["image_url"] else "",
            }
        )
    return stories
