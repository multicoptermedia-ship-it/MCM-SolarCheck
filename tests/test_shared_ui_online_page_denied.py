"""The shared online page must not bypass customer entry authorization."""
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from mcm_solarcheck.infrastructure.verification_http_server import verification_handler


class Session:
    def require_user(self, token):
        return "alice"


def test_unverified_customer_cannot_load_app():
    def deny(_):
        raise PermissionError("unverified")
    server = ThreadingHTTPServer(("127.0.0.1", 0), verification_handler(None, session_service=Session(), customer_entry=deny, project_service=object()))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        for path in ("/app", "/api/runtime"):
            request = Request(f"http://127.0.0.1:{server.server_port}" + path, headers={"Cookie": "solarcheck_session=valid"})
            try:
                urlopen(request, timeout=3)
            except HTTPError as error:
                assert error.code == 403
            else:
                raise AssertionError("customer entry gate bypassed")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
