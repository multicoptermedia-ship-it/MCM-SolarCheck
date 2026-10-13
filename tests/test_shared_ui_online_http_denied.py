"""Online JSON route refuses unverified customers before project access."""
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from mcm_solarcheck.infrastructure.verification_http_server import verification_handler


class Session:
    def require_user(self, token):
        return "alice"


class Projects:
    def projects_for_customer(self, customer_id):
        raise AssertionError("project read after denied customer entry")


def test_unverified_customer_cannot_list_projects():
    def deny(_):
        raise PermissionError("unverified")

    handler = verification_handler(None, session_service=Session(), customer_entry=deny, project_service=Projects())
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = Request(f"http://127.0.0.1:{server.server_port}/api/projects", headers={"Cookie": "solarcheck_session=valid"})
        try:
            urlopen(request, timeout=3)
        except HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("unverified customer must be denied")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
