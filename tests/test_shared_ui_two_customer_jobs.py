"""Two distinct customers can be admitted in parallel; third remains queued."""
import json
from http.server import ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from urllib.request import Request, urlopen
from mcm_solarcheck.infrastructure.verification_http_server import verification_handler
from mcm_solarcheck.services.compute_jobs import ComputeJobStatus


class Sessions:
    def require_user(self, token):
        if token not in ("alice", "bob", "carol"):
            raise PermissionError("invalid")
        return token


class Projects:
    def projects_for_customer(self, user_id):
        return [SimpleNamespace(project_id="project-" + user_id)]


class Jobs:
    def __init__(self):
        self.running = 0
        self.seen = []

    def create(self, *, job_id, user_id, project_id):
        self.seen.append((user_id, project_id))
        return SimpleNamespace(job_id=job_id, status=ComputeJobStatus.QUEUED)

    def start(self, job_id, *, user_id, project_id, capacity):
        assert capacity.max_parallel_jobs == 2
        if self.running < capacity.max_parallel_jobs:
            self.running += 1
            status = ComputeJobStatus.RUNNING
        else:
            status = ComputeJobStatus.QUEUED
        return SimpleNamespace(job_id=job_id, status=status)


def test_two_customers_running_third_queued():
    jobs = Jobs()
    server = ThreadingHTTPServer(("127.0.0.1", 0), verification_handler(None, session_service=Sessions(), customer_entry=lambda _: None, project_service=Projects(), compute_job_service=jobs))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        statuses = []
        for user in ("alice", "bob", "carol"):
            request = Request(f"http://127.0.0.1:{server.server_port}/api/compute-jobs", data=("project_id=project-" + user).encode(), method="POST", headers={"Cookie": "solarcheck_session=" + user, "Content-Type": "application/x-www-form-urlencoded"})
            with urlopen(request, timeout=3) as response:
                assert response.status == 201
                result = json.load(response)
                assert result["project_id"] == "project-" + user
                statuses.append(result["status"])
        assert statuses == ["running", "running", "queued"]
        assert jobs.seen == [(u, "project-" + u) for u in ("alice", "bob", "carol")]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
