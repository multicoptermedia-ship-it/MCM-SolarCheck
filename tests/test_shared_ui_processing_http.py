"""JSON processing route uses authenticated, scoped existing processing service."""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from mcm_solarcheck.infrastructure.verification_http_server import verification_handler
from mcm_solarcheck.services.project_processing import ProjectProcessingState


class Session:
    def require_user(self, token):
        if token != "valid":
            raise PermissionError("invalid")
        return "alice"


class Processing:
    def process(self, request):
        assert (request.customer_id, request.project_id, request.job_id) == ("alice", "p1", "j1")
        return SimpleNamespace(state=ProjectProcessingState.COMPLETED, imported_thermal_frames=2, paired_frames=1, import_failures=0)


def test_processing_json_requires_session_and_returns_real_service_counts():
    server = ThreadingHTTPServer(("127.0.0.1", 0), verification_handler(None, session_service=Session(), customer_entry=lambda _: None, project_processing_service=Processing()))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/project-process?project_id=p1&job_id=j1"
    try:
        try:
            urlopen(Request(url, data=b"", method="POST"), timeout=3)
        except HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("missing session accepted")
        with urlopen(Request(url, data=b"", method="POST", headers={"Cookie": "solarcheck_session=valid"}), timeout=3) as response:
            assert json.load(response) == {"project_id": "p1", "job_id": "j1", "state": "completed", "imported_thermal_frames": 2, "paired_frames": 1, "import_failures": 0}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
