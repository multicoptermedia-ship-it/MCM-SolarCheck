"""Standard-library HTTP adapter for SolarCheck email verification."""

from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from mcm_solarcheck.services.online_verification_http import EmailVerificationEndpoint


def verification_handler(
    endpoint: EmailVerificationEndpoint,
) -> type[BaseHTTPRequestHandler]:
    """Bind the transport-neutral verification endpoint to HTTP GET requests."""

    class VerificationHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/verify-email":
                self._respond(404, "Not Found")
                return
            token = parse_qs(parsed.query).get("token", [None])[0]
            result = endpoint.verify(token)
            self._respond(result.status_code, result.message)

        def _respond(self, status_code: int, message: str) -> None:
            body = (
                "<!doctype html><html><head><meta charset=\"utf-8\">"
                "<title>SolarCheck</title></head><body>"
                f"<h1>SolarCheck</h1><p>{escape(message)}</p></body></html>"
            ).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args) -> None:
            return

    return VerificationHandler


def build_verification_server(
    endpoint: EmailVerificationEndpoint,
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    server_factory: Callable[..., ThreadingHTTPServer] = ThreadingHTTPServer,
) -> ThreadingHTTPServer:
    """Build a local/test HTTP server without owning its process lifecycle."""
    return server_factory((host, port), verification_handler(endpoint))
