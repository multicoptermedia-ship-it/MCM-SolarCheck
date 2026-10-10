from contextlib import contextmanager
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.queued_sftp_preflight_composition import build_queued_sftp_preflight


class FakeStore:
    def queued_jobs(self, limit):
        assert limit == 10
        return [
            SimpleNamespace(user_id="a", project_id="p1", job_id="j1"),
            SimpleNamespace(user_id="a", project_id="p1", job_id="j1"),
            SimpleNamespace(user_id="b", project_id="p2", job_id="j2"),
        ]


class FakeConnector:
    def __init__(self):
        self.paths = []
        self.closed = 0

    @contextmanager
    def open_verified_read_only(self, config):
        try:
            yield self
        finally:
            self.closed += 1

    def directory_exists(self, path):
        self.paths.append(path)
        return True


def test_queue_snapshot_preflight_preserves_project_paths_and_deduplicates():
    connector = FakeConnector()
    config = SimpleNamespace(root="/storage")
    preflight = build_queued_sftp_preflight(
        FakeStore(), connector, config, batch_size=10, max_sessions=2
    )
    result = preflight.tick()
    assert [item.job_id for item in result] == ["j1", "j2"]
    assert [item.directory_exists for item in result] == [True, True]
    assert connector.paths == ["/storage/a/p1", "/storage/b/p2"]
    assert connector.closed == 2


def test_queue_preflight_rejects_invalid_customer_before_opening_connection():
    class InvalidStore:
        def queued_jobs(self, limit):
            return [SimpleNamespace(user_id="../escape", project_id="p", job_id="j")]

    connector = FakeConnector()
    preflight = build_queued_sftp_preflight(
        InvalidStore(), connector, SimpleNamespace(root="/storage")
    )
    with pytest.raises(ValueError):
        preflight.tick()
    assert connector.paths == []
    assert connector.closed == 0


def test_queue_preflight_does_not_swallow_remote_errors():
    class FailingConnector(FakeConnector):
        def directory_exists(self, path):
            raise PermissionError("remote denied")

    connector = FailingConnector()
    preflight = build_queued_sftp_preflight(
        FakeStore(), connector, SimpleNamespace(root="/storage"), batch_size=10
    )
    with pytest.raises(PermissionError):
        preflight.tick()
    assert connector.closed == 1
