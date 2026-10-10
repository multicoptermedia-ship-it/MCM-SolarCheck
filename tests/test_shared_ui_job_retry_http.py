"""Existing queued job admission remains owner-scoped and idempotent for terminal states."""
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
    def __init__(self):
        self.starts = 0

    def get(self, job_id, *, user_id, project_id):
        if (job_id, user_id, project_id) != ("j1", "alice", "p1"):
            raise PermissionError("wrong owner")
        return SimpleNamespace(job_id=job_id, status=ComputeJobStatus.QUEUED)

    def start(self, job_id, *, user_id, project_id, capacity):
        self.starts += 1
        return SimpleNamespace(job_id=job_id, status=ComputeJobStatus.RUNNING)


def test_retry_requires_session_and_project_scope():
    jobs = Jobs()
    server = ThreadingHTTPServer(("127.0.0.1", 0), verification_handler(None, session_service=Session(), customer_entry=lambda _: None, compute_job_service=jobs))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/compute-job-start?project_id=p1&job_id=j1"
    try:
        for target, cookie, code in ((url, None, 401), (url.replace("project_id=p1", "project_id=p2"), "valid", 404)):
            headers = {"Cookie": "solarcheck_session=" + cookie} if cookie else {}
            try:
                urlopen(Request(target, data=b"", method="POST", headers=headers), timeout=3)
            except HTTPError as error:
                assert error.code == code
            else:
                raise AssertionError("unauthorized retry accepted")
        assert jobs.starts == 0
        with urlopen(Request(url, data=b"", method="POST", headers={"Cookie": "solarcheck_session=valid"}), timeout=3) as response:
            assert json.load(response) == {"project_id": "p1", "job_id": "j1", "status": "running"}
        assert jobs.starts == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
