"""Authenticated online page and runtime are served by the existing HTTP handler."""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from mcm_solarcheck.infrastructure.verification_http_server import verification_handler


class Session:
    def require_user(self, token):
        if token != "valid":
            raise PermissionError("invalid")
        return "alice"


class Projects:
    def projects_for_customer(self, customer_id):
        return ()


def test_authenticated_shared_ui_and_runtime():
    server = ThreadingHTTPServer(("127.0.0.1", 0), verification_handler(None, session_service=Session(), customer_entry=lambda _: None, project_service=Projects()))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        for path in ("/app", "/api/runtime"):
            try:
                urlopen(base + path, timeout=3)
            except HTTPError as error:
                assert error.code == 401
            else:
                raise AssertionError("unauthenticated access")
        with urlopen(Request(base + "/app", headers={"Cookie": "solarcheck_session=valid"}), timeout=3) as response:
            assert response.status == 200
            assert b"Gespeicherte Projekte" in response.read()
            assert response.headers["Cache-Control"] == "no-store"
        with urlopen(Request(base + "/api/runtime", headers={"Cookie": "solarcheck_session=valid"}), timeout=3) as response:
            assert json.load(response) == {"mode": "online", "features_ready": False}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
