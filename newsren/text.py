import hashlib
import re
import unicodedata
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

USER_AGENT = "NewsrenLocal/0.1 (student project; research use; admin@localhost)"

STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "with",
        "is", "are", "was", "were", "be", "as", "at", "by", "from", "that",
        "this", "it", "its", "not", "but", "we", "you", "they", "their",
        "has", "have", "had", "will", "can", "about", "into", "over", "after",
        "before", "than", "then", "so", "if", "no", "do", "did", "does",
    }
)


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        self.parts.append(" ")

    def handle_endtag(self, tag):
        self.parts.append(" ")

    def handle_data(self, data):
        self.parts.append(data)


def normalize_url(url: str) -> str:
    parts = urlsplit((url or "").strip())
    query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        lowered = key.lower()
        if lowered.startswith("utm_") or lowered == "fbclid":
            continue
        query.append((key, value))
    query.sort()
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), ""))


def story_id(url: str) -> str:
    return hashlib.sha256(normalize_url(url).encode("utf-8")).hexdigest()[:16]


def normalize_title(title: str) -> str:
    chars = []
    for char in (title or "").lower():
        chars.append(char if char.isalnum() or char.isspace() else " ")
    return " ".join("".join(chars).split())


def strip_html(value: str) -> str:
    parser = _TextExtractor()
    parser.feed(value or "")
    parser.close()
    text = unescape("".join(parser.parts))
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    parts, start = [], 0
    abbreviations = r"\b(?:Mr|Mrs|Ms|Dr|Prof|Jr|Sr|Inc|Corp|Co|Ltd|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.$|\b(?:[A-Za-z]\.){2,}$"
    for boundary in re.finditer(r"(?<=[.!?。？！])\s+", text):
        before = text[:boundary.start()]
        after = text[boundary.end():]
        abbreviated = re.search(abbreviations, before, re.IGNORECASE)
        new_sentence = re.match(r"(?:The|This|That|These|Those|It|They|We|However)\b", after)
        if abbreviated and not new_sentence:
            continue
        parts.append(text[start:boundary.start()].strip())
        start = boundary.end()
    if text[start:]:
        parts.append(text[start:].strip())
    return parts


def parse_date(value: str):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError, OverflowError):
        parsed = None
    if parsed is not None:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def english_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


SHORT_TOPICS = frozenset({"ai", "ml", "vc", "pe", "sec", "ipo", "gpt", "eu", "uk", "us"})


def query_terms(text: str) -> set[str]:
    return {word for word in english_words(text)
            if word not in STOPWORDS and (len(word) > 3 or word in SHORT_TOPICS)}


def semantic_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "").replace("−", "-").replace("’", "'").lower()
    for contracted, expanded in (("can't", "can not"), ("won't", "will not"), ("shan't", "shall not")):
        text = text.replace(contracted, expanded)
    return re.sub(r"\b(\w+)n't\b", r"\1 not", text)


def numeric_values(text: str) -> list[str]:
    return re.findall(r"(?<!\w)[+-]?\d+(?:[,.]\d+)*%?", semantic_text(text))
