"""Loopback-only development preview for the shared UI. No analysis or report API."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

UI_FILE = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


def make_handler(mode: str):
    if mode not in ("online", "offline"):
        raise ValueError("mode must be online or offline")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.partition("?")[0]
            if path == "/api/runtime":
                payload = json.dumps({"mode": mode, "features_ready": False}).encode("utf-8")
                mime = "application/json"
            elif path in ("/", "/index.html"):
                payload = UI_FILE.read_bytes()
                mime = "text/html; charset=utf-8"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def serve(mode: str, port: int = 8765):
    # Preview must not be exposed to external clients.
    with ThreadingHTTPServer(("127.0.0.1", port), make_handler(mode)) as server:
        print("SolarCheck preview: http://127.0.0.1:" + str(server.server_port))
        server.serve_forever()
