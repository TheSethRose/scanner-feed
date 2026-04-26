import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .config import HEALTH_PORT


STARTED_AT = time.strftime("%Y-%m-%dT%H:%M:%S%z")
LAST_LOOP_AT = None
LAST_TRANSCRIPT_AT = None
_LOCK = threading.Lock()


def mark_loop() -> None:
    global LAST_LOOP_AT

    with _LOCK:
        LAST_LOOP_AT = time.strftime("%Y-%m-%dT%H:%M:%S%z")


def mark_transcript() -> None:
    global LAST_TRANSCRIPT_AT

    with _LOCK:
        LAST_TRANSCRIPT_AT = time.strftime("%Y-%m-%dT%H:%M:%S%z")


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return

        with _LOCK:
            payload = {
                "ok": True,
                "started_at": STARTED_AT,
                "last_loop_at": LAST_LOOP_AT,
                "last_transcript_at": LAST_TRANSCRIPT_AT,
            }

        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def start_health_server() -> None:
    if HEALTH_PORT <= 0:
        return

    server = ThreadingHTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Health check listening on http://0.0.0.0:{HEALTH_PORT}/health", flush=True)
