import threading
from contextlib import contextmanager
from http.server import ThreadingHTTPServer

from server import build_handler
from newsren.research import ResearchAgent


@contextmanager
def serve(store, research_agent=None):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(store, research_agent=research_agent or ResearchAgent()))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(2)
