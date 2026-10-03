from __future__ import annotations

from contextlib import closing
from threading import Thread
from urllib.error import HTTPError
from urllib.request import urlopen

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
