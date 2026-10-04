"""Standard-library HTTP adapter for SolarCheck email verification."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
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
PROJECT_FIELDS = ("project_id", "name", "capacity_kwp")


def verification_handler(
    endpoint: EmailVerificationEndpoint,
    registration_controller=None,
    login_service=None,
    session_service=None,
    secure_cookies: bool = False,
    customer_entry=None,
    project_service=None,
    project_pricing_service=None,
    project_creation_service=None,
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
            if parsed.path == "/projects" and session_service is not None and customer_entry is not None and project_service is not None:
                self._handle_projects()
                return
            if parsed.path == "/project-price" and session_service is not None and customer_entry is not None and project_pricing_service is not None:
                self._handle_project_price(parsed)
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
            if parsed.path == "/projects" and session_service is not None and customer_entry is not None and project_creation_service is not None:
                self._handle_create_project()
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

        def _handle_create_project(self) -> None:
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type != "application/x-www-form-urlencoded":
                self._respond(415, "project content type is not supported")
                return
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                self._respond(400, "project data is invalid")
                return
            if length <= 0:
                self._respond(400, "project data is invalid")
                return
            if length > MAX_REGISTRATION_BODY_BYTES:
                self._respond(413, "project data is too large")
                return
            try:
                form = parse_qs(
                    self.rfile.read(length).decode("utf-8"),
                    keep_blank_values=True,
                    strict_parsing=True,
                )
                if any(len(form.get(name, [])) != 1 for name in PROJECT_FIELDS):
                    raise ValueError("project fields must occur exactly once")
                from mcm_solarcheck.services.project_creation import CreateProjectRequest

                project = project_creation_service.create(
                    CreateProjectRequest(
                        customer_id=user_id,
                        project_id=form["project_id"][0],
                        name=form["name"][0],
                        capacity_kwp=Decimal(form["capacity_kwp"][0]),
                    )
                )
            except (UnicodeDecodeError, InvalidOperation, ValueError):
                self._respond(400, "project data is invalid")
                return
            except (PermissionError, RuntimeError):
                self._respond(503, "online project could not be created")
                return
            self._respond(
                201,
                f"Projekt erstellt: {project.project_id}: {project.name}",
                headers={"Cache-Control": "no-store"},
            )

        def _require_customer_user(self) -> str:
            cookies = SimpleCookie()
            try:
                cookies.load(self.headers.get("Cookie", ""))
                morsel = cookies.get("solarcheck_session")
                if morsel is None:
                    raise PermissionError("online session is invalid")
                user_id = session_service.require_user(morsel.value)
            except (CookieError, PermissionError, ValueError) as exc:
                raise PermissionError("online session is invalid") from exc
            return user_id

        def _handle_project_price(self, parsed) -> None:
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            project_ids = parse_qs(parsed.query).get("project_id", [])
            if len(project_ids) != 1 or not project_ids[0].strip():
                self._respond(400, "project id is invalid")
                return
            try:
                from mcm_solarcheck.services.project_pricing import ProjectPricingRequest

                snapshot = project_pricing_service.price(
                    ProjectPricingRequest(project_ids[0])
                )
            except (PermissionError, RuntimeError, TypeError, ValueError):
                self._respond(503, "online project price is not available")
                return
            message = (
                f"{project_ids[0]}: {snapshot.net_total} EUR netto, "
                f"{snapshot.gross_total} EUR brutto "
                f"(Preisregel {snapshot.rule_version})"
            )
            self._respond(200, message, headers={"Cache-Control": "no-store"})

        def _handle_projects(self) -> None:
            try:
                user_id = self._require_customer_user()
            except PermissionError:
                self._respond(401, "online session is invalid")
                return
            try:
                customer_entry(user_id)
            except (PermissionError, RuntimeError, ValueError):
                self._respond(403, "online customer entry is not available")
                return
            try:
                projects = project_service.projects()
            except (PermissionError, RuntimeError, ValueError):
                self._respond(503, "online projects are not available")
                return
            try:
                message = "Keine Projekte vorhanden." if not projects else "\n".join(
                    f"{project.project_id}: {project.name}" for project in projects
                )
            except (AttributeError, TypeError, ValueError):
                self._respond(503, "online projects are not available")
                return
            self._respond(200, message, headers={"Cache-Control": "no-store"})

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
            remaining = int(
                (session.expires_at - datetime.now(timezone.utc)).total_seconds()
            )
            if remaining <= 0:
                session_service.revoke(session.token)
                self._respond(500, "online session could not be created")
                return
            cookie = (
                f"solarcheck_session={session.token}; Path=/; HttpOnly; SameSite=Strict"
                f"; Max-Age={remaining}"
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
    project_service=None,
    project_pricing_service=None,
    project_creation_service=None,
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
            project_service,
            project_pricing_service,
            project_creation_service,
        ),
    )
