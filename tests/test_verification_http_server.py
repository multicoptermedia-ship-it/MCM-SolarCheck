from __future__ import annotations

from contextlib import closing
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
