import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from newsren.ask import ask_stories
from newsren.intelligence import IntelligenceStore
from newsren.pages import reader_catalog, render_home, render_not_found, render_story
from newsren.research import ResearchAgent
from newsren.research_pages import render_research_index, render_research_run
from newsren.synthesis import synthesizer_from_env
from newsren.related import related_stories
from newsren.store import Store

HOST = "127.0.0.1"
PORT = 8765
INTERVAL_SECONDS = 1800
CACHE_PATH = Path("data/cache.json")
READER_PATH = Path("static/reader.js")
DESIGN_ASSETS = {
    "/static/design.css": ("text/css; charset=utf-8", Path("static/design.css")),
    "/static/interface.js": ("text/javascript; charset=utf-8", Path("static/interface.js")),
}


def build_handler(store, research_agent=None):
    intelligence = IntelligenceStore(store.path.with_name("intelligence.sqlite3")) if hasattr(store, "path") else None
    agent = research_agent or ResearchAgent(synthesizer=synthesizer_from_env())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def _send(self, status, content_type, body: bytes):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "same-origin")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path in DESIGN_ASSETS:
                content_type, path = DESIGN_ASSETS[parsed.path]
                self._send(200, content_type, path.read_bytes())
                return
            if intelligence and parsed.path in {"/research", "/review"}:
                story_id = parse_qs(parsed.query).get("story", [""])[0]
                context = store.get(story_id) if story_id else None
                html = render_research_index(intelligence.list_runs(), context, review=parsed.path == "/review", model_enabled=agent.synthesizer is not None, model_provider=getattr(agent.synthesizer, "provider_label", "configured model provider"))
                self._send(200, "text/html; charset=utf-8", html.encode())
                return
            if intelligence and (parsed.path.startswith("/research/") or parsed.path.startswith("/api/research/")):
                run_id = parsed.path.rsplit("/", 1)[-1]
                run = intelligence.get_run(run_id) if re.fullmatch(r"[0-9a-f]{32}", run_id) else None
                if run is None:
                    self._send(404, "text/html; charset=utf-8", render_not_found().encode())
                elif parsed.path.startswith("/api/"):
                    self._send(200, "application/json; charset=utf-8", json.dumps(run, ensure_ascii=False).encode())
                else:
                    self._send(200, "text/html; charset=utf-8", render_research_run(run).encode())
                return
            if parsed.path == "/":
                history = store.research_stories() if hasattr(store, "research_stories") else None
                body = render_home(store.snapshot(), history).encode("utf-8")
                self._send(200, "text/html; charset=utf-8", body)
                return
            if parsed.path == "/api/stories":
                snapshot = store.snapshot()
                history = store.research_stories() if hasattr(store, "research_stories") else None
                snapshot["stories"] = reader_catalog(snapshot["stories"], history)
                body = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", body)
                return
            if parsed.path == "/static/reader.js":
                self._send(200, "text/javascript; charset=utf-8", READER_PATH.read_bytes())
                return
            if parsed.path.startswith("/story/"):
                story_id = parsed.path[len("/story/") :]
                if len(story_id) != 16 or any(char not in "0123456789abcdef" for char in story_id):
                    self._send(404, "text/html; charset=utf-8", render_not_found().encode("utf-8"))
                    return
                story = store.get(story_id)
                if story is None:
                    self._send(404, "text/html; charset=utf-8", render_not_found().encode("utf-8"))
                    return
                question = parse_qs(parsed.query).get("q", [""])[0]
                catalog = store.research_stories() if hasattr(store, "research_stories") else store.snapshot()["stories"]
                related = related_stories(story, catalog)
                matches = None
                if question.strip():
                    matches = ask_stories(question, [story, *related])
                body = render_story(story, question, matches, related).encode("utf-8")
                self._send(200, "text/html; charset=utf-8", body)
                return
            self._send(404, "text/html; charset=utf-8", render_not_found().encode("utf-8"))

        def do_POST(self):
            parsed = urlparse(self.path)
            port = self.server.server_address[1]
            allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
            origin = self.headers.get("Origin")
            if self.headers.get("Host") not in allowed_hosts or (origin and urlparse(origin).netloc != self.headers.get("Host")) or self.headers.get("Sec-Fetch-Site") == "cross-site":
                self._send(403, "text/plain; charset=utf-8", b"Cross-origin writes are not allowed.")
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
                if length < 0:
                    raise ValueError()
            except ValueError:
                self._send(400, "text/plain; charset=utf-8", b"Invalid content length.")
                return
            if length > 16384:
                self._send(413, "text/plain; charset=utf-8", b"Request is too large.")
                return
            if intelligence and parsed.path in {"/research", "/review"}:
                try:
                    form = parse_qs(self.rfile.read(length).decode("utf-8"))
                    if parsed.path == "/research":
                        question = form.get("question", [""])[0]
                        story_id = form.get("story_id", [""])[0]
                        context = store.get(story_id) if story_id else None
                        if story_id and context is None:
                            raise ValueError("Starting story was not found.")
                        run = agent.run(question, store.research_stories(), context, live=form.get("live", [""])[0] == "1", use_model=form.get("use_model", [""])[0] == "1", paper_id=form.get("paper_id", [""])[0])
                        intelligence.save_run(run)
                        run_id = run["id"]
                    else:
                        run_id = form.get("run_id", [""])[0]
                        intelligence.review_run(run_id, form.get("status", [""])[0], form.get("note", [""])[0])
                except (ValueError, UnicodeDecodeError, KeyError) as exc:
                    html = render_research_index(intelligence.list_runs(), error=str(exc), model_enabled=agent.synthesizer is not None, model_provider=getattr(agent.synthesizer, "provider_label", "configured model provider"))
                    self._send(400, "text/html; charset=utf-8", html.encode())
                    return
                self.send_response(303)
                self.send_header("Location", f"/research/{run_id}")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if parsed.path != "/api/refresh":
                self._send(404, "text/html; charset=utf-8", render_not_found().encode("utf-8"))
                return
            if length:
                self.rfile.read(length)
            snapshot = store.refresh()
            body = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
            self._send(200, "application/json; charset=utf-8", body)

    return Handler


def make_server(store, host=HOST, port=PORT):
    try:
        return ThreadingHTTPServer((host, port), build_handler(store))
    except OSError:
        print(f"Port {port} is already in use", file=sys.stderr)
        raise SystemExit(1)


def start_background_refresh(store, interval_seconds=INTERVAL_SECONDS, stop_event=None):
    stop_event = stop_event or threading.Event()

    def loop():
        while not stop_event.is_set():
            try:
                store.refresh()
            except Exception as exc:
                print(f"Refresh failed: {exc}", file=sys.stderr)
            finally:
                store.refreshing = False
            if stop_event.wait(interval_seconds):
                return

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread


def main():
    store = Store(CACHE_PATH)
    server = make_server(store)
    store.refreshing = True
    start_background_refresh(store, INTERVAL_SECONDS)
    server.serve_forever()


if __name__ == "__main__":
    main()
