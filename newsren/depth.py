import re

from newsren.text import STOPWORDS, english_words

IMPACT_WORDS = frozenset(
    {
        "affect",
        "affects",
        "affected",
        "impact",
        "impacts",
        "supplier",
        "suppliers",
        "customer",
        "customers",
        "workers",
        "jobs",
        "capacity",
        "supply",
        "cost",
        "costs",
        "downstream",
        "upstream",
    }
)

TRACKER_WORDS = {
    "earnings": "earnings",
    "filing": "filing",
    "filings": "filing",
    "funding": "funding",
    "enforcement": "enforcement",
    "guidance": "guidance",
    "settlement": "settlement",
    "order": "order",
    "comment": "comment",
}

TRACKER_LIMIT = 12
IMPACT_LIMIT = 5


def _title_words(story: dict) -> list[str]:
    found = []
    seen = set()
    for word in english_words(story.get("title") or ""):
        if word in STOPWORDS or len(word) <= 3 or word in seen:
            continue
        seen.add(word)
        found.append(word)
    return found


def lesson_cloze(story: dict) -> dict | None:
    sentences = list(story.get("summary_sentences") or [])
    if not sentences:
        title = (story.get("title") or "").strip()
        if title:
            sentences = [title]
    for word in _title_words(story):
        for sentence in sentences:
            if word not in set(english_words(sentence)):
                continue
            prompt = re.sub(re.escape(word), "_____", sentence, count=1, flags=re.IGNORECASE)
            match = re.search(re.escape(word), sentence, flags=re.IGNORECASE)
            if not match:
                continue
            return {"prompt": prompt, "answer": match.group(0), "sentence": sentence}
    return None


def impact_sentences(story: dict, related: list | None) -> list[dict]:
    found = []
    seen = set()
    for item in [story, *(related or [])]:
        for sentence in item.get("summary_sentences") or []:
            if sentence in seen:
                continue
            if not (set(english_words(sentence)) & IMPACT_WORDS):
                continue
            seen.add(sentence)
            found.append(
                {
                    "sentence": sentence,
                    "id": item.get("id") or "",
                    "title": item.get("title") or "",
                    "url": item.get("url") or "",
                    "source_name": item.get("source_name") or "",
                }
            )
            if len(found) >= IMPACT_LIMIT:
                return found
    return found


def tracker_rows(stories: list[dict]) -> list[dict]:
    found = []
    for item in stories:
        if item.get("category") != "finance":
            continue
        text = item.get("title") or ""
        text = text + " " + " ".join(item.get("summary_sentences") or [])
        label = ""
        for word in english_words(text):
            if word in TRACKER_WORDS:
                label = TRACKER_WORDS[word]
                break
        if not label:
            continue
        found.append(
            {
                "id": item.get("id") or "",
                "title": item.get("title") or "",
                "url": item.get("url") or "",
                "source_name": item.get("source_name") or "",
                "published_at": item.get("published_at") or "",
                "label": label,
            }
        )
        if len(found) >= TRACKER_LIMIT:
            break
    return found


def cache_stats(snapshot: dict) -> dict:
    stories = snapshot.get("stories") or []
    sources = snapshot.get("sources") or []
    by_category = {"technology": 0, "education": 0, "industry": 0, "finance": 0}
    for item in stories:
        category = item.get("category") or ""
        if category in by_category:
            by_category[category] += 1
    down = sum(1 for source in sources if source.get("last_error"))
    return {
        "stories": len(stories),
        "by_category": by_category,
        "sources_ok": len(sources) - down,
        "sources_down": down,
    }
