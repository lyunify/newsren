import re

from newsren.text import STOPWORDS, numeric_values, parse_date, query_terms, semantic_text

MAX_DOCUMENT_FREQUENCY = 4
MIN_SHARED_TERMS = 2
RELATED_LIMIT = 5
BOILERPLATE = frozenset({"federal", "reserve", "board", "announces", "announcement", "small", "business",
                        "committee", "advisory", "notice", "published", "update", "updated", "latest", "first", "last", "world", "inc"})
FILLER = frozenset({"total", "today", "yesterday", "also", "said", "says", "reported", "reports", "report",
                   "continue", "continues", "updated", "update", "according"})


def _terms(text: str) -> set[str]:
    return query_terms(text) - BOILERPLATE


def content_terms(text: str) -> set[str]:
    words = re.findall(r"[+-]?\d+(?:[,.]\d+)*%?|[a-z][a-z0-9]*", semantic_text(text))
    return {"not" if word in {"cannot", "never", "no", "not"} else word for word in words
            if (word not in STOPWORDS or word in {"not", "no"}) and word not in FILLER}


def _sort_key(item: dict):
    parsed_date = parse_date(item.get("published_at") or "")
    if parsed_date is None:
        return (1, "", item.get("first_seen_at") or item.get("retrieved_at") or "")
    return (0, parsed_date.isoformat(), item.get("first_seen_at") or item.get("retrieved_at") or "")


def timeline_stories(story: dict, related: list | None) -> list[dict]:
    items = [story]
    seen = {story.get("id")}
    for item in related or []:
        if item.get("id") in seen:
            continue
        seen.add(item.get("id"))
        items.append(item)
    items.sort(key=_sort_key)
    return [{"story": item, "is_current": item.get("id") == story.get("id")} for item in items]


def earlier_related(story: dict, related: list | None) -> list[dict]:
    current_key = _sort_key(story)
    found = []
    for item in related or []:
        if item.get("id") == story.get("id"):
            continue
        if _sort_key(item) < current_key:
            found.append(item)
    return found


def new_sentences(story: dict, related: list | None) -> list[str]:
    return unrepeated_sentences(story, earlier_related(story, related or []))


def material_update(story: dict, stories: list[dict]) -> bool:
    related = related_stories(story, stories)
    if not earlier_related(story, related):
        return True
    return bool(new_sentences(story, related))


def change_sentences(story: dict, stories: list[dict]) -> list[str]:
    related = related_stories(story, stories)
    if earlier_related(story, related):
        return new_sentences(story, related)
    return list(story.get("summary_sentences") or [])


def unrepeated_sentences(story: dict, related: list[dict]) -> list[str]:
    if not related:
        return []
    other = set()
    for item in related:
        other |= content_terms(item.get("title") or "")
        for sentence in item.get("summary_sentences") or []:
            other |= content_terms(sentence)
    found = []
    for sentence in story.get("summary_sentences") or []:
        terms = content_terms(sentence)
        unique = terms - other
        polarity_change = False
        numeric_change = False
        for item in related:
            for previous in item.get("summary_sentences") or []:
                previous_terms = content_terms(previous)
                overlap = (terms - {"not"}) & (previous_terms - {"not"})
                if len(overlap) >= 2 and len(overlap) / max(len(terms | previous_terms), 1) >= 0.6:
                    polarity_change |= ("not" in terms) != ("not" in previous_terms)
                    numeric_change |= numeric_values(sentence) != numeric_values(previous)
        if unique or polarity_change or numeric_change:
            found.append(sentence)
    return found


def related_stories(story: dict, stories: list[dict]) -> list[dict]:
    parsed = [(item, _terms(item.get("title") or "")) for item in stories]
    current_terms = None
    for item, terms in parsed:
        if item.get("id") == story.get("id"):
            current_terms = terms
            break
    if current_terms is None:
        current_terms = _terms(story.get("title") or "")
    usable = current_terms
    if len(usable) < MIN_SHARED_TERMS:
        return []
    found = []
    for item, terms in parsed:
        if item.get("id") == story.get("id"):
            continue
        shared = usable & terms
        if len(shared) >= MIN_SHARED_TERMS:
            found.append(item)

    found.sort(key=_sort_key)
    if len(found) > RELATED_LIMIT:
        found = found[-RELATED_LIMIT:]
    return found
