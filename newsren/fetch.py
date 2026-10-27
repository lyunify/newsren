from datetime import datetime, timezone
import time
from urllib.request import Request

from newsren.parse import parse_feed
from newsren.network import read_bounded
from newsren.text import USER_AGENT, parse_date


def fetch_source(source: dict, retrieved_at: str, opener, timeout: float = 12):
    request = Request(source["url"], headers={"User-Agent": USER_AGENT})
    deadline = time.monotonic() + timeout
    try:
        with opener.open(request, timeout=timeout) as response:
            payload = read_bounded(response, limit=4 * 1024 * 1024, deadline=deadline)
        stories = parse_feed(payload, source, retrieved_at)
    except Exception as exc:
        return [], f"{type(exc).__name__}: {exc}"

    def sort_key(story):
        parsed = parse_date(story.get("published_at") or "")
        if parsed is None:
            return (0, datetime.min.replace(tzinfo=timezone.utc))
        return (1, parsed)

    stories.sort(key=sort_key, reverse=True)
    return stories[:20], ""
