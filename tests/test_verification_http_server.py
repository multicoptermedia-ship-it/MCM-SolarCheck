from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta, timezone
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcm_solarcheck.infrastructure.verification_http_server import (
    build_verification_server,
)
from mcm_solarcheck.services.online_verification_http import VerificationHttpResult


class Endpoint:
    def __init__(self) -> None:
        self.tokens = []

    def verify(self, token):
        self.tokens.append(token)
        if token == "good-token":
            return VerificationHttpResult(200, "E-Mail-Adresse wurde bestätigt.", "user-1")
        return VerificationHttpResult(400, "verification token is invalid or expired")


class RegistrationController:
    def __init__(self) -> None:
        self.requests = []

    def register(self, request):
        self.requests.append(request)
        return "Bestätigungs-E-Mail wurde gesendet."


def request(server, path: str):
    host, port = server.server_address
    return urlopen(f"http://{host}:{port}{path}", timeout=2)


def test_local_http_adapter_exposes_customer_entry_without_verification() -> None:
    endpoint = Endpoint()
    server = build_verification_server(endpoint)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with closing(request(server, "/")) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "SolarCheck Online" in body
            assert "Anmeldung und Registrierung" in body
        assert endpoint.tokens == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_http_adapter_routes_registration_without_verification() -> None:
    endpoint = Endpoint()
    registration = RegistrationController()
    server = build_verification_server(endpoint, registration_controller=registration)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({
            "user_id": "user-1",
            "display_name": "MCM Test",
            "email": "user@example.com",
            "street": "Musterweg 1",
            "postal_code": "50181",
            "city": "Bedburg",
            "password": "correct horse battery staple",
        }).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/register",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 202
            assert "Bestätigungs-E-Mail wurde gesendet." in response.read().decode("utf-8")
        assert len(registration.requests) == 1
        assert registration.requests[0].email == "user@example.com"
        assert endpoint.tokens == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_http_adapter_rejects_wrong_registration_content_type() -> None:
    endpoint = Endpoint()
    registration = RegistrationController()
    server = build_verification_server(endpoint, registration_controller=registration)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/register",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 415
        else:
            raise AssertionError("unsupported content type must return 415")
        assert registration.requests == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_http_adapter_rejects_incomplete_registration() -> None:
    endpoint = Endpoint()
    registration = RegistrationController()
    server = build_verification_server(endpoint, registration_controller=registration)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({"email": "user@example.com"}).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/register",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("incomplete registration must return 400")
        assert registration.requests == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_http_adapter_rejects_oversized_registration() -> None:
    endpoint = Endpoint()
    registration = RegistrationController()
    server = build_verification_server(endpoint, registration_controller=registration)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/register",
            data=b"x" * (16 * 1024 + 1),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 413
        else:
            raise AssertionError("oversized registration must return 413")
        assert registration.requests == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_http_adapter_routes_verification_token() -> None:
    endpoint = Endpoint()
    server = build_verification_server(endpoint)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with closing(request(server, "/verify-email?token=good-token")) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "E-Mail-Adresse wurde bestätigt." in body
        assert endpoint.tokens == ["good-token"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_http_adapter_rejects_unknown_path_without_verification() -> None:
    endpoint = Endpoint()
    server = build_verification_server(endpoint)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        try:
            request(server, "/other")
        except HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("unknown path must return 404")
        assert endpoint.tokens == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class LoginService:
    def __init__(self, accepted=True) -> None:
        self.accepted = accepted
        self.calls = []

    def login(self, user_id, password):
        self.calls.append((user_id, password))
        if not self.accepted:
            raise PermissionError("invalid online login")
        return user_id


class SessionService:
    class Session:
        token = "opaque-session-token"
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    def __init__(self) -> None:
        self.users = []
        self.revoked = []

    def create(self, user_id):
        self.users.append(user_id)
        return self.Session()

    def require_user(self, token):
        if token != "opaque-session-token" or token in self.revoked:
            raise PermissionError("online session is invalid")
        return "user-1"

    def revoke(self, token):
        self.revoked.append(token)


def test_local_http_adapter_routes_login() -> None:
    endpoint = Endpoint()
    login = LoginService()
    sessions = SessionService()
    server = build_verification_server(endpoint, login_service=login, session_service=sessions, secure_cookies=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({
            "user_id": "user-1",
            "password": "correct horse battery staple",
        }).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/login",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 200
            body = response.read().decode("utf-8")
            assert "Anmeldung erfolgreich" in body
            assert "opaque-session-token" not in body
            cookie = response.headers["Set-Cookie"]
            assert cookie.startswith("solarcheck_session=opaque-session-token;")
            assert "HttpOnly" in cookie
            assert "SameSite=Strict" in cookie
            assert "Max-Age=" in cookie
            assert "Secure" in cookie
        assert sessions.users == ["user-1"]
        assert login.calls == [("user-1", "correct horse battery staple")]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_local_http_adapter_masks_rejected_login() -> None:
    endpoint = Endpoint()
    login = LoginService(accepted=False)
    server = build_verification_server(endpoint, login_service=login)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({
            "user_id": "user-1",
            "password": "wrong password value",
        }).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/login",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
            assert "invalid online login" in exc.read().decode("utf-8")
        else:
            raise AssertionError("rejected login must return 401")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_customer_entry_resolves_session_before_authorization() -> None:
    endpoint = Endpoint()
    sessions = SessionService()
    users = []
    server = build_verification_server(
        endpoint,
        session_service=sessions,
        customer_entry=users.append,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/customer-entry",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 200
            assert "Kundenzugang freigegeben" in response.read().decode("utf-8")
        assert users == ["user-1"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_customer_entry_rejects_missing_session_cookie() -> None:
    endpoint = Endpoint()
    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        try:
            urlopen(f"http://{host}:{port}/customer-entry", timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("missing session cookie must return 401")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_customer_entry_rejects_authorization_gate() -> None:
    endpoint = Endpoint()

    def reject(user_id):
        raise PermissionError("entitlement inactive")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=reject,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/customer-entry",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("customer entry gate rejection must return 403")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_logout_revokes_session_and_expires_cookie() -> None:
    endpoint = Endpoint()
    sessions = SessionService()
    server = build_verification_server(
        endpoint,
        session_service=sessions,
        secure_cookies=True,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/logout",
            data=b"",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
            method="POST",
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 200
            assert "Abmeldung erfolgreich" in response.read().decode("utf-8")
            cookie = response.headers["Set-Cookie"]
            assert cookie.startswith("solarcheck_session=;")
            assert "Max-Age=0" in cookie
            assert "HttpOnly" in cookie
            assert "SameSite=Strict" in cookie
            assert "Secure" in cookie
        assert sessions.revoked == ["opaque-session-token"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_logout_without_session_is_idempotent() -> None:
    endpoint = Endpoint()
    sessions = SessionService()
    server = build_verification_server(endpoint, session_service=sessions)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(f"http://{host}:{port}/logout", data=b"", method="POST")
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 200
            assert "Max-Age=0" in response.headers["Set-Cookie"]
        assert sessions.revoked == []
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_login_rejects_already_expired_created_session() -> None:
    endpoint = Endpoint()
    login = LoginService()

    class ExpiredSessionService(SessionService):
        class Session:
            token = "expired-session-token"
            expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    sessions = ExpiredSessionService()
    server = build_verification_server(
        endpoint,
        login_service=login,
        session_service=sessions,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({
            "user_id": "user-1",
            "password": "correct horse battery staple",
        }).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/login",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 500
            assert exc.headers.get("Set-Cookie") is None
        else:
            raise AssertionError("expired created session must not issue a cookie")
        assert sessions.revoked == ["expired-session-token"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_projects_require_session_and_customer_authorization() -> None:
    endpoint = Endpoint()
    sessions = SessionService()
    authorized = []

    class Project:
        project_id = "P-1"
        name = "Online Project"

    class Projects:
        def projects(self):
            return (Project(),)

    server = build_verification_server(
        endpoint,
        session_service=sessions,
        customer_entry=authorized.append,
        project_service=Projects(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/projects",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        with closing(urlopen(req, timeout=2)) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert "P-1: Online Project" in body
        assert authorized == ["user-1"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_projects_reject_missing_session_before_project_access() -> None:
    endpoint = Endpoint()

    class Projects:
        def projects(self):
            raise AssertionError("projects must not be read without a valid session")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_service=Projects(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        try:
            urlopen(f"http://{host}:{port}/projects", timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("missing session must return 401")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_projects_return_forbidden_when_customer_authorization_fails() -> None:
    endpoint = Endpoint()

    class Projects:
        def projects(self):
            raise AssertionError("projects must not be read without customer authorization")

    def reject(user_id):
        assert user_id == "user-1"
        raise PermissionError("entitlement inactive")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=reject,
        project_service=Projects(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/projects",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 403
            assert "online customer entry is not available" in exc.read().decode("utf-8")
        else:
            raise AssertionError("customer authorization failure must return 403")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_projects_return_service_unavailable_when_project_backend_fails() -> None:
    endpoint = Endpoint()

    class Projects:
        def projects(self):
            raise RuntimeError("project backend unavailable")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_service=Projects(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/projects",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 503
            assert "online projects are not available" in exc.read().decode("utf-8")
        else:
            raise AssertionError("project backend failure must return 503")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_projects_return_service_unavailable_for_invalid_project_data() -> None:
    endpoint = Endpoint()

    class InvalidProject:
        project_id = "P-1"

    class Projects:
        def projects(self):
            return (InvalidProject(),)

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_service=Projects(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/projects",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 503
            assert "online projects are not available" in exc.read().decode("utf-8")
        else:
            raise AssertionError("invalid project data must return 503")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_projects_disable_caching_for_authorized_response() -> None:
    endpoint = Endpoint()

    class Project:
        project_id = "P-1"
        name = "Private Project"

    class Projects:
        def projects(self):
            return (Project(),)

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_service=Projects(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/projects",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert "P-1: Private Project" in response.read().decode("utf-8")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_price_requires_authorized_customer_and_disables_caching() -> None:
    endpoint = Endpoint()
    authorized = []

    class Snapshot:
        net_total = "500.00"
        gross_total = "595.00"
        rule_version = "2026-10-online"

    class Pricing:
        def __init__(self):
            self.requests = []

        def price(self, pricing_request):
            self.requests.append(pricing_request)
            return Snapshot()

    pricing = Pricing()
    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=authorized.append,
        project_pricing_service=pricing,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-price?project_id=P-1",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        with closing(urlopen(req, timeout=2)) as response:
            body = response.read().decode("utf-8")
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert "P-1: 500.00 EUR netto" in body
            assert "595.00 EUR brutto" in body
            assert "2026-10-online" in body
        assert authorized == ["user-1"]
        assert pricing.requests[0].customer_id == "user-1"
        assert pricing.requests[0].project_id == "P-1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_price_rejects_missing_session_before_pricing_access() -> None:
    endpoint = Endpoint()

    class Pricing:
        def price(self, pricing_request):
            raise AssertionError("pricing must not be read without a valid session")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_pricing_service=Pricing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        try:
            urlopen(f"http://{host}:{port}/project-price?project_id=P-1", timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("missing session must return 401")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_price_rejects_invalid_project_id_before_pricing_access() -> None:
    endpoint = Endpoint()

    class Pricing:
        def price(self, pricing_request):
            raise AssertionError("pricing must not be read for an invalid project id")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_pricing_service=Pricing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-price",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("missing project id must return 400")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)



def test_project_price_hides_foreign_project_as_not_found() -> None:
    endpoint = Endpoint()

    class Pricing:
        def price(self, pricing_request):
            assert pricing_request.customer_id == "user-1"
            assert pricing_request.project_id == "P-foreign"
            raise PermissionError("project is not available")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_pricing_service=Pricing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-price?project_id=P-foreign",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 404
            body = exc.read().decode("utf-8")
            assert "SolarCheck – Fehler 404" in body
            assert "project is not available" in body
            assert "Bitte prüfen Sie die Projektauswahl oder kehren Sie zur Projektübersicht zurück." in body
            assert "anderen Kunden" not in body
        else:
            raise AssertionError("foreign project pricing must return 404")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def test_project_price_returns_service_unavailable_when_pricing_fails() -> None:
    endpoint = Endpoint()

    class Pricing:
        def price(self, pricing_request):
            raise RuntimeError("pricing backend unavailable")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_pricing_service=Pricing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-price?project_id=P-1",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 503
            assert "online project price is not available" in exc.read().decode("utf-8")
        else:
            raise AssertionError("pricing failure must return 503")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_creation_uses_customer_from_authenticated_session() -> None:
    endpoint = Endpoint()
    authorized = []

    class Project:
        project_id = "P-2"
        name = "Solarpark West"

    class Creation:
        def __init__(self):
            self.requests = []

        def create(self, creation_request):
            self.requests.append(creation_request)
            return Project()

    creation = Creation()
    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=authorized.append,
        project_creation_service=creation,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({
            "project_id": "P-2",
            "name": "Solarpark West",
            "capacity_kwp": "850.5",
        }).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/projects",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": "solarcheck_session=opaque-session-token",
            },
            method="POST",
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 201
            assert response.headers["Cache-Control"] == "no-store"
            assert "Projekt erstellt: P-2: Solarpark West" in response.read().decode("utf-8")
        assert authorized == ["user-1"]
        assert creation.requests[0].customer_id == "user-1"
        assert creation.requests[0].project_id == "P-2"
        assert str(creation.requests[0].capacity_kwp) == "850.5"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_creation_rejects_missing_session_before_creation() -> None:
    endpoint = Endpoint()

    class Creation:
        def create(self, creation_request):
            raise AssertionError("project must not be created without a valid session")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_creation_service=Creation(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({
            "project_id": "P-2",
            "name": "Solarpark West",
            "capacity_kwp": "850.5",
        }).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/projects",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("missing session must return 401")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_creation_rejects_invalid_capacity_before_service_call() -> None:
    endpoint = Endpoint()

    class Creation:
        def create(self, creation_request):
            raise AssertionError("invalid project data must not reach creation service")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_creation_service=Creation(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        body = urlencode({
            "project_id": "P-2",
            "name": "Solarpark West",
            "capacity_kwp": "not-a-number",
        }).encode("utf-8")
        req = Request(
            f"http://{host}:{port}/projects",
            data=body,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Cookie": "solarcheck_session=opaque-session-token",
            },
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("invalid capacity must return 400")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_upload_uses_authenticated_customer_and_disables_caching() -> None:
    endpoint = Endpoint()

    class UploadResult:
        filename = "thermal-001.jpg"
        size_bytes = 10

    class UploadService:
        def __init__(self):
            self.requests = []

        def upload(self, upload_request):
            self.requests.append(upload_request)
            return UploadResult()

    uploads = UploadService()
    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_upload_service=uploads,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-upload",
            data=b"image-data",
            headers={
                "Content-Type": "image/jpeg",
                "Cookie": "solarcheck_session=opaque-session-token",
                "X-SolarCheck-Project-Id": "P-1",
                "X-SolarCheck-Filename": "thermal-001.jpg",
            },
            method="POST",
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 201
            assert response.headers["Cache-Control"] == "no-store"
            assert "Upload gespeichert: thermal-001.jpg (10 Bytes)" in response.read().decode("utf-8")
        assert uploads.requests[0].customer_id == "user-1"
        assert uploads.requests[0].project_id == "P-1"
        assert uploads.requests[0].content == b"image-data"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_upload_rejects_missing_session_before_upload_access() -> None:
    endpoint = Endpoint()

    class UploadService:
        def upload(self, upload_request):
            raise AssertionError("upload service must not be called")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_upload_service=UploadService(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-upload",
            data=b"image-data",
            headers={
                "Content-Type": "image/jpeg",
                "X-SolarCheck-Project-Id": "P-1",
                "X-SolarCheck-Filename": "thermal-001.jpg",
            },
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 401
        else:
            raise AssertionError("missing session must return 401")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_upload_hides_unavailable_project() -> None:
    endpoint = Endpoint()

    class UploadService:
        def upload(self, upload_request):
            raise PermissionError("project belongs to another customer")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_upload_service=UploadService(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-upload",
            data=b"image-data",
            headers={
                "Content-Type": "image/jpeg",
                "Cookie": "solarcheck_session=opaque-session-token",
                "X-SolarCheck-Project-Id": "P-other",
                "X-SolarCheck-Filename": "thermal-001.jpg",
            },
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as exc:
            assert exc.code == 404
            assert "project is not available" in exc.read().decode("utf-8")
        else:
            raise AssertionError("unavailable project must return 404")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_processing_uses_authenticated_customer_and_disables_caching() -> None:
    endpoint = Endpoint()

    class Result:
        imported_thermal_frames = 12
        paired_frames = 10
        import_failures = 1

    class Processing:
        def __init__(self):
            self.requests = []

        def process(self, processing_request):
            self.requests.append(processing_request)
            return Result()

    processing = Processing()
    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_processing_service=processing,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-process?project_id=P-1",
            data=b"",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
            method="POST",
        )
        with closing(urlopen(req, timeout=2)) as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            body = response.read().decode("utf-8")
            assert "Projekt verarbeitet: P-1" in body
            assert "Thermalbilder: 12" in body
            assert "Paare: 10" in body
            assert "Importfehler: 1" in body
        assert processing.requests[0].customer_id == "user-1"
        assert processing.requests[0].project_id == "P-1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_processing_rejects_missing_session_before_processing() -> None:
    endpoint = Endpoint()

    class Processing:
        def process(self, processing_request):
            raise AssertionError("processing must not be called without session")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_processing_service=Processing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-process?project_id=P-1",
            data=b"",
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("missing session must return 401")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_processing_hides_foreign_project() -> None:
    endpoint = Endpoint()

    class Processing:
        def process(self, processing_request):
            raise PermissionError("foreign project")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_processing_service=Processing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-process?project_id=P-other",
            data=b"",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError("foreign project must return 404")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_processing_rejects_invalid_project_id_before_processing() -> None:
    endpoint = Endpoint()

    class Processing:
        def process(self, processing_request):
            raise AssertionError("processing must not be called for invalid project id")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_processing_service=Processing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-process",
            data=b"",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as error:
            assert error.code == 400
        else:
            raise AssertionError("invalid project id must return 400")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_processing_rejects_unavailable_customer_before_processing() -> None:
    endpoint = Endpoint()

    class Processing:
        def process(self, processing_request):
            raise AssertionError("processing must not be called without customer access")

    def reject_customer(user_id):
        raise PermissionError("customer unavailable")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=reject_customer,
        project_processing_service=Processing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-process?project_id=P-1",
            data=b"",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("unavailable customer must return 403")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_project_processing_maps_import_failure_to_service_unavailable() -> None:
    endpoint = Endpoint()

    class Processing:
        def process(self, processing_request):
            raise RuntimeError("import failed")

    server = build_verification_server(
        endpoint,
        session_service=SessionService(),
        customer_entry=lambda user_id: None,
        project_processing_service=Processing(),
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        req = Request(
            f"http://{host}:{port}/project-process?project_id=P-1",
            data=b"",
            headers={"Cookie": "solarcheck_session=opaque-session-token"},
            method="POST",
        )
        try:
            urlopen(req, timeout=2)
        except HTTPError as error:
            assert error.code == 503
            assert "online project processing is not available" in error.read().decode("utf-8")
        else:
            raise AssertionError("processing failure must return 503")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
