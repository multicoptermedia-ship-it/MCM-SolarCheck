"""HTTP job status is scoped to the authenticated customer and project."""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from mcm_solarcheck.infrastructure.verification_http_server import verification_handler
from mcm_solarcheck.services.compute_jobs import ComputeJobStatus


class Session:
    def require_user(self, token):
        if token != "valid":
            raise PermissionError("invalid")
        return "alice"


class Jobs:
    def get(self, job_id, *, user_id, project_id):
        if (job_id, user_id, project_id) != ("job1", "alice", "p1"):
            raise PermissionError("not owner")
        return SimpleNamespace(job_id=job_id, status=ComputeJobStatus.QUEUED)


def test_job_status_auth_and_scope():
    server = ThreadingHTTPServer(("127.0.0.1", 0), verification_handler(None, session_service=Session(), customer_entry=lambda _: None, compute_job_service=Jobs()))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/compute-job?project_id=p1&job_id=job1"
    try:
        try:
            urlopen(url, timeout=3)
        except HTTPError as error:
            assert error.code == 401
        else:
            raise AssertionError("unauthenticated job access")
        with urlopen(Request(url, headers={"Cookie": "solarcheck_session=valid"}), timeout=3) as response:
            assert json.load(response) == {"project_id": "p1", "job_id": "job1", "status": "queued"}
        try:
            urlopen(Request(url.replace("project_id=p1", "project_id=p2"), headers={"Cookie": "solarcheck_session=valid"}), timeout=3)
        except HTTPError as error:
            assert error.code == 404
        else:
            raise AssertionError("cross-project job access")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
