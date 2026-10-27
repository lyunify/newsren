from newsren.text import normalize_title, parse_date


def _prefer(existing: dict, incoming: dict) -> dict:
    old = parse_date(existing.get("published_at") or "")
    new = parse_date(incoming.get("published_at") or "")
    if new and (old is None or new > old):
        return incoming
    return existing


def dedupe_stories(stories: list[dict]) -> list[dict]:
    by_id = []
    id_index = {}
    for story in stories:
        key = story["id"]
        if key in id_index:
            slot = id_index[key]
            by_id[slot] = _prefer(by_id[slot], story)
        else:
            id_index[key] = len(by_id)
            by_id.append(story)
    kept = []
    title_index = {}
    for story in by_id:
        key = (story["category"], normalize_title(story["title"]))
        if key in title_index:
            slot = title_index[key]
            kept[slot] = _prefer(kept[slot], story)
        else:
            title_index[key] = len(kept)
            kept.append(story)
    return kept
