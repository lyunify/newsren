from newsren.related import change_sentences, material_update
from newsren.text import english_words, query_terms

CHANGE_LIMIT = 3


def unseen_matches(question: str, stories: list[dict], seen_ids: set[str]) -> list[dict]:
    terms = query_terms(question)
    if not terms:
        return []
    found = []
    for story in stories:
        if story.get("followKey", story["id"]) in seen_ids:
            continue
        text = story.get("title") or ""
        text = text + " " + " ".join(story.get("summary_sentences") or [])
        words = set(english_words(text))
        if any(term in words for term in terms) and material_update(story, stories):
            found.append(story)
    return found


def change_quotes(question: str, stories: list[dict], seen_ids: set[str], limit: int = CHANGE_LIMIT) -> list[dict]:
    quotes = []
    for story in unseen_matches(question, stories, seen_ids):
        for sentence in change_sentences(story, stories):
            quotes.append(
                {
                    "sentence": sentence,
                    "id": story["id"],
                    "title": story.get("title") or "",
                    "url": story.get("url") or "",
                    "source_name": story.get("source_name") or "",
                }
            )
            if len(quotes) >= limit:
                return quotes
    return quotes
