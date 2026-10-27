import json
from pathlib import Path

_STORY_KEYS = ("id", "title", "url", "source_name", "category")


def _usable_story(story) -> bool:
    if not isinstance(story, dict):
        return False
    for key in _STORY_KEYS:
        value = story.get(key)
        if not isinstance(value, str) or not value.strip():
            return False
    return True


def load_cache(path: Path) -> dict:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {"stories": [], "sources": {}}
    if not isinstance(payload, dict):
        return {"stories": [], "sources": {}}
    stories = payload.get("stories")
    sources = payload.get("sources")
    if not isinstance(stories, list) or not isinstance(sources, dict):
        return {"stories": [], "sources": {}}
    loaded = {"stories": [story for story in stories if _usable_story(story)], "sources": sources}
    if isinstance(payload.get("history"), list):
        loaded["history"] = [story for story in payload["history"] if _usable_story(story)]
    return loaded


def save_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)
