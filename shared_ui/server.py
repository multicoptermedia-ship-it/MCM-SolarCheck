"""Loopback-only preview server; offline project reads use existing SQLite services."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

UI_FILE = Path(__file__).resolve().parents[1] / "frontend" / "index.html"


def make_handler(mode: str, *, database_path: str | Path | None = None):
    if mode not in ("online", "offline"):
        raise ValueError("mode must be online or offline")
    if mode == "online" and database_path is not None:
        raise ValueError("online preview cannot access offline database")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/api/runtime":
                self._json(200, {"mode": mode, "features_ready": False})
            elif path == "/api/projects":
                if mode != "offline" or database_path is None:
                    self._json(403, {"error": "project listing unavailable"})
                    return
                from shared_ui.offline_projects import offline_project_list
                try:
                    projects = offline_project_list(database_path)
                except (OSError, RuntimeError, ValueError):
                    self._json(503, {"error": "project store unavailable"})
                    return
                self._json(200, {"projects": projects})
            elif path in ("/", "/index.html"):
                self._send(200, UI_FILE.read_bytes(), "text/html; charset=utf-8")
            else:
                self.send_error(404)

        def _json(self, status, value):
            self._send(status, json.dumps(value).encode("utf-8"), "application/json")

        def _send(self, status, payload, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return Handler


def serve(mode: str, port: int = 8765, *, database_path: str | Path | None = None):
    with ThreadingHTTPServer(("127.0.0.1", port), make_handler(mode, database_path=database_path)) as server:
        print("SolarCheck preview: http://127.0.0.1:" + str(server.server_port))
        server.serve_forever()
