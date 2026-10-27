from newsren.text import STOPWORDS, english_words, split_sentences

HEDGE_WORDS = frozenset(
    {
        "may",
        "might",
        "could",
        "alleged",
        "allegedly",
        "reportedly",
        "claimed",
        "claims",
        "expected",
        "forecast",
        "forecasts",
        "possible",
        "possibly",
        "unconfirmed",
    }
)

CLAIM_WORDS = {
    "backtest": "backtest",
    "backtests": "backtest",
    "simulated": "simulated",
    "simulation": "simulated",
    "live": "live",
    "forecast": "forecast",
    "forecasts": "forecast",
    "guidance": "guidance",
}

GLOSSARY_LIMIT = 5


def _source_sentences(story: dict) -> list[str]:
    found = []
    seen = set()
    for part in (story.get("title") or "", story.get("excerpt") or ""):
        for sentence in split_sentences(part):
            if sentence not in seen:
                seen.add(sentence)
                found.append(sentence)
    if found:
        return found
    for sentence in story.get("summary_sentences") or []:
        if sentence not in seen:
            seen.add(sentence)
            found.append(sentence)
    return found


def uncertainty_sentences(story: dict) -> list[str]:
    found = []
    for sentence in _source_sentences(story):
        words = set(english_words(sentence))
        if words & HEDGE_WORDS:
            found.append(sentence)
    return found[:3]


def independent_sources(story: dict, related: list | None) -> list[dict]:
    rows = []
    seen = set()
    for item in [story, *(related or [])]:
        name = item.get("source_name") or ""
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append({"source_name": name, "url": item.get("url") or ""})
    return rows


def other_section_stories(story: dict, related: list | None) -> list[dict]:
    category = story.get("category") or ""
    found = []
    for item in related or []:
        if (item.get("category") or "") and item.get("category") != category:
            found.append(item)
    return found


def claim_labels(story: dict) -> list[dict]:
    found = []
    for sentence in story.get("summary_sentences") or _source_sentences(story):
        words = english_words(sentence)
        label = ""
        for word in words:
            if word in CLAIM_WORDS:
                label = CLAIM_WORDS[word]
                break
        if label:
            found.append({"sentence": sentence, "label": label})
    return found


def glossary_entries(story: dict) -> list[dict]:
    title_words = []
    seen_words = set()
    for word in english_words(story.get("title") or ""):
        if word in STOPWORDS or len(word) <= 3 or word in seen_words:
            continue
        seen_words.add(word)
        title_words.append(word)
    sentences = []
    seen_sentences = set()
    for sentence in list(story.get("summary_sentences") or []) + _source_sentences(story):
        if sentence in seen_sentences:
            continue
        seen_sentences.add(sentence)
        sentences.append(sentence)
    found = []
    for word in title_words:
        for sentence in sentences:
            if word in set(english_words(sentence)):
                found.append({"word": word, "sentence": sentence})
                break
        if len(found) >= GLOSSARY_LIMIT:
            break
    return found
