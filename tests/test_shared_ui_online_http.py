"""JSON projects route uses session cookie and customer authorization."""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from types import SimpleNamespace

from mcm_solarcheck.infrastructure.verification_http_server import verification_handler


class Session:
    def require_user(self, token):
        if token != "valid":
            raise PermissionError("invalid")
        return "alice"


class Projects:
    def projects_for_customer(self, customer_id):
        assert customer_id == "alice"
        return (SimpleNamespace(project_id="a1", name="Anlage Nord"),)

    def projects(self):
        raise AssertionError("unscoped read")


def test_online_json_project_route():
    handler = verification_handler(None, session_service=Session(), customer_entry=lambda _: None, project_service=Projects())
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/api/projects"
    try:
        try:
            urlopen(base, timeout=3)
        except HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("missing cookie must be denied")
        request = Request(base, headers={"Cookie": "solarcheck_session=valid"})
        with urlopen(request, timeout=3) as response:
            assert response.status == 200
            assert response.headers["Cache-Control"] == "no-store"
            assert json.load(response) == {"projects": [{"id": "a1", "name": "Anlage Nord"}]}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
