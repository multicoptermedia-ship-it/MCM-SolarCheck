"""Standard-library HTTP adapter for SolarCheck email verification."""

from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from mcm_solarcheck.services.online_registration_controller import RegistrationRequest

from mcm_solarcheck.services.online_verification_http import EmailVerificationEndpoint


MAX_REGISTRATION_BODY_BYTES = 16 * 1024
REGISTRATION_FIELDS = ("user_id", "display_name", "email", "street", "postal_code", "city")


def verification_handler(
    endpoint: EmailVerificationEndpoint,
    registration_controller=None,
) -> type[BaseHTTPRequestHandler]:
    """Bind the transport-neutral verification endpoint to HTTP GET requests."""

    class VerificationHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._respond(
                    200,
                    "SolarCheck Online – Anmeldung und Registrierung werden hier bereitgestellt.",
                )
                return
            if parsed.path != "/verify-email":
                self._respond(404, "Not Found")
                return
            token = parse_qs(parsed.query).get("token", [None])[0]
            result = endpoint.verify(token)
            self._respond(result.status_code, result.message)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path != "/register" or registration_controller is None:
                self._respond(404, "Not Found")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-www-form-urlencoded":
                self._respond(415, "registration content type is not supported")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "registration data is invalid")
                return
            if length <= 0:
                self._respond(400, "registration data is invalid")
                return
            if length > MAX_REGISTRATION_BODY_BYTES:
                self._respond(413, "registration data is too large")
                return
            try:
                form = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                )
                if any(len(form.get(name, [])) != 1 for name in REGISTRATION_FIELDS):
                    raise ValueError("registration fields must occur exactly once")
                field = lambda name: form[name][0]
                message = registration_controller.register(
                    RegistrationRequest(
                        user_id=field("user_id"),
                        display_name=field("display_name"),
                        email=field("email"),
                        street=field("street"),
                        postal_code=field("postal_code"),
                        city=field("city"),
                    )
                )
            except (UnicodeDecodeError, ValueError):
                self._respond(400, "registration data is invalid")
                return
            self._respond(202, message)

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
    registration_controller=None,
) -> ThreadingHTTPServer:
    """Build a local/test HTTP server without owning its process lifecycle."""
    return server_factory(
        (host, port),
        verification_handler(endpoint, registration_controller),
    )
