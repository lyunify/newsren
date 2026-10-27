from newsren.text import split_sentences


def _preferred(text: str) -> list[str]:
    chosen = []
    for sentence in split_sentences(text or ""):
        if 40 <= len(sentence) <= 280 and sentence not in chosen:
            chosen.append(sentence)
    return chosen


def build_summary(title: str, excerpt: str) -> dict:
    preferred = _preferred(excerpt) or _preferred(title)
    if preferred:
        return {"summary_sentences": preferred[:3], "summary_truncated": False}
    cleaned = (excerpt or "").strip()
    if not cleaned:
        return {"summary_sentences": [], "summary_truncated": False}
    return {"summary_sentences": [cleaned[:280].rstrip()], "summary_truncated": True}
