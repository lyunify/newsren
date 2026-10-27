import hashlib
import threading
from pathlib import Path
from urllib.request import build_opener

from newsren.cache import load_cache, save_cache
from newsren.dedupe import dedupe_stories
from newsren.fetch import fetch_source
from newsren.sources import APPROVED_SOURCES
from newsren.summary import build_summary


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        loaded = load_cache(self.path)
        self.stories = loaded["stories"]
        self.history = loaded.get("history", [])
        for story in [*self.stories, *self.history]:
            story.setdefault("first_seen_at", story.get("retrieved_at") or "")
            if story.get("excerpt"):
                story.update(build_summary(story["title"], story["excerpt"]))
        self.source_state = {}
        for source in APPROVED_SOURCES:
            saved = loaded["sources"].get(source["url"], {})
            self.source_state[source["url"]] = {
                "last_success_at": saved.get("last_success_at") or "",
                "last_error": saved.get("last_error") or "",
                "last_error_at": saved.get("last_error_at") or "",
            }
        self.refreshing = False
        self._refresh_lock = threading.Lock()

    def snapshot(self) -> dict:
        sources = []
        for source in APPROVED_SOURCES:
            state = self.source_state[source["url"]]
            sources.append(
                {
                    "name": source["name"],
                    "category": source["category"],
                    "url": source["url"],
                    "last_success_at": state["last_success_at"],
                    "last_error": state["last_error"],
                    "last_error_at": state["last_error_at"],
                }
            )
        return {"stories": list(self.stories), "sources": sources, "refreshing": self.refreshing,
                "history_count": len(self.history)}

    def get(self, story_id: str):
        for story in [*self.stories, *self.history]:
            if story["id"] == story_id:
                return story
        return None

    def research_stories(self) -> list[dict]:
        return list({story["id"]: story for story in [*self.history, *self.stories]}.values())

    @staticmethod
    def _content_key(story):
        text = (story.get("title") or "") + "\n" + (story.get("excerpt") or "")
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _retain_history(self, incoming: list[dict]):
        previous = {story["id"]: story for story in self.research_stories()}
        history = {story["id"]: dict(story) for story in self.history}
        latest = {story["id"]: story for story in incoming}
        for key, old in previous.items():
            new = latest.get(key)
            if new is None:
                history[key] = old
            elif self._content_key(old) != self._content_key(new):
                archived = dict(old)
                archived["canonical_id"] = old.get("canonical_id", key)
                occurrence = old.get("first_seen_at") or old.get("retrieved_at") or ""
                archived["id"] = hashlib.sha256((key + self._content_key(old) + occurrence).encode()).hexdigest()[:16]
                archived["is_revision"] = True
                history.pop(key, None)
                history[archived["id"]] = archived
            else:
                new["first_seen_at"] = old.get("first_seen_at") or old.get("retrieved_at") or ""
                history.pop(key, None)
        for new in incoming:
            new.setdefault("first_seen_at", new.get("retrieved_at") or "")
        self.history = list(history.values())[-5000:]

    def refresh(self, opener=None, now: str | None = None) -> dict:
        with self._refresh_lock:
            return self._refresh(opener, now)

    def _refresh(self, opener=None, now: str | None = None) -> dict:
        from datetime import datetime, timezone

        opener = opener or build_opener()
        if now is None:
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        previous = {}
        for story in self.stories:
            previous.setdefault(story["source_name"], []).append(story)
        collected = []
        for source in APPROVED_SOURCES:
            items, error = fetch_source(source, now, opener)
            state = self.source_state[source["url"]]
            if error:
                state["last_error"] = error
                state["last_error_at"] = now
                collected.extend(previous.get(source["name"], []))
            else:
                state["last_error"] = ""
                state["last_error_at"] = ""
                state["last_success_at"] = now
                collected.extend(items)
        incoming = dedupe_stories(collected)
        self._retain_history(incoming)
        self.stories = incoming
        save_cache(
            self.path,
            {
                "stories": self.stories,
                "history": self.history,
                "sources": {
                    source["url"]: self.source_state[source["url"]] for source in APPROVED_SOURCES
                },
            },
        )
        return self.snapshot()
