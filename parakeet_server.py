#!/usr/bin/env python3

import json
import os
import traceback
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from parakeet_mlx import from_pretrained

from scanner_app.asr import extract_text
from scanner_app.config import MODEL_NAME


HOST = os.getenv("PARAKEET_SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("PARAKEET_SERVER_PORT", "18765"))
MODEL = None
LAST_TRANSCRIPT_AT = None


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return

        self.write_json(
            {
                "ok": True,
                "model_loaded": MODEL is not None,
                "model": MODEL_NAME,
                "last_transcript_at": LAST_TRANSCRIPT_AT,
            }
        )

    def do_POST(self):
        if self.path != "/transcribe":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            segment_path = Path(payload["segment_path"])
            started_at = time.time()
            result = MODEL.transcribe(str(segment_path))
            text = extract_text(result)
            duration_ms = int((time.time() - started_at) * 1000)
            global LAST_TRANSCRIPT_AT
            LAST_TRANSCRIPT_AT = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            self.write_json(
                {
                    "text": text,
                    "model": MODEL_NAME,
                    "duration_ms": duration_ms,
                }
            )
        except Exception as exc:
            print(f"transcribe failed: {exc}", flush=True)
            traceback.print_exc()
            self.write_json({"error": str(exc)}, status=500)

    def write_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def main() -> None:
    global MODEL
    print(f"Loading model: {MODEL_NAME}", flush=True)
    MODEL = from_pretrained(MODEL_NAME)
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Parakeet server listening on http://{HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
