"""Standard-library HTTP adapter for SolarCheck email verification."""

from __future__ import annotations

from html import escape
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse

from mcm_solarcheck.services.online_registration_controller import RegistrationRequest

from mcm_solarcheck.services.online_verification_http import EmailVerificationEndpoint


MAX_REGISTRATION_BODY_BYTES = 16 * 1024
REGISTRATION_FIELDS = ("user_id", "display_name", "email", "street", "postal_code", "city", "password")
LOGIN_FIELDS = ("user_id", "password")


def verification_handler(
    endpoint: EmailVerificationEndpoint,
    registration_controller=None,
    login_service=None,
    session_service=None,
    secure_cookies: bool = False,
    customer_entry=None,
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
            if parsed.path == "/customer-entry" and session_service is not None and customer_entry is not None:
                self._handle_customer_entry()
                return
            if parsed.path != "/verify-email":
                self._respond(404, "Not Found")
                return
            token = parse_qs(parsed.query).get("token", [None])[0]
            result = endpoint.verify(token)
            self._respond(result.status_code, result.message)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/login" and login_service is not None:
                self._handle_login()
                return
            if parsed.path == "/logout" and session_service is not None:
                self._handle_logout()
                return
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
                        password=field("password"),
                    )
                )
            except (UnicodeDecodeError, ValueError):
                self._respond(400, "registration data is invalid")
                return
            self._respond(202, message)

        def _handle_customer_entry(self) -> None:
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                morsel = cookies.get("solarcheck_session")
                if morsel is None:
                    raise PermissionError("online session is invalid")
                user_id = session_service.require_user(morsel.value)
            except (CookieError, PermissionError, ValueError):
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            self._respond(200, "SolarCheck Online Kundenzugang freigegeben.")

        def _handle_logout(self) -> None:
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                morsel = cookies.get("solarcheck_session")
                if morsel is not None and morsel.value:
                    session_service.revoke(morsel.value)
            except (CookieError, ValueError):
                pass
            cookie = (
                "solarcheck_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0"
                + ("; Secure" if secure_cookies else "")
            )
            self._respond(200, "Abmeldung erfolgreich.", headers={"Set-Cookie": cookie})

        def _handle_login(self) -> None:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-www-form-urlencoded":
                self._respond(415, "login content type is not supported")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "login data is invalid")
                return
            if length <= 0:
                self._respond(400, "login data is invalid")
                return
            if length > MAX_REGISTRATION_BODY_BYTES:
                self._respond(413, "login data is too large")
                return
            try:
                form = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                )
                if any(len(form.get(name, [])) != 1 for name in LOGIN_FIELDS):
                    raise ValueError("login fields must occur exactly once")
                user_id = login_service.login(
                    form["user_id"][0],
                    form["password"][0],
                )
            except (UnicodeDecodeError, ValueError):
                self._respond(400, "login data is invalid")
                return
            except PermissionError:
                self._respond(401, "invalid online login")
                return
            if session_service is None:
                self._respond(200, f"Anmeldung erfolgreich: {user_id}")
                return
            session = session_service.create(user_id)
            cookie = (
                f"solarcheck_session={session.token}; Path=/; HttpOnly; SameSite=Strict"
                + ("; Secure" if secure_cookies else "")
            )
            self._respond(200, "Anmeldung erfolgreich.", headers={"Set-Cookie": cookie})

        def _respond(self, status_code: int, message: str, *, headers=None) -> None:
            body = (
                "<!doctype html><html><head><meta charset=\"utf-8\">"
                "<title>SolarCheck</title></head><body>"
                f"<h1>SolarCheck</h1><p>{escape(message)}</p></body></html>"
            ).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
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
    login_service=None,
    session_service=None,
    secure_cookies: bool = False,
    customer_entry=None,
) -> ThreadingHTTPServer:
    """Build a local/test HTTP server without owning its process lifecycle."""
    return server_factory(
        (host, port),
        verification_handler(
            endpoint,
            registration_controller,
            login_service,
            session_service,
            secure_cookies,
            customer_entry,
        ),
    )
