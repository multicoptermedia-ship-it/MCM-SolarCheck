from contextlib import contextmanager
from threading import Event, Thread

import pytest

from mcm_solarcheck.services.sftp_project_session_manager import (
    SFTPProjectContext, SFTPProjectSessionManager,
)
from mcm_solarcheck.services.sftp_project_paths import require_project_sftp_path


class Connector:
    def __init__(self):
        self.opens = 0
        self.closes = 0

    @contextmanager
    def open_verified_read_only(self, config):
        self.opens += 1
        try:
            yield self
        finally:
            self.closes += 1

    def directory_exists(self, path):
        return True


def manager(connector, max_sessions=2):
    return SFTPProjectSessionManager(connector, type("Config", (), {"root": "/data"})(), max_sessions=max_sessions)


def test_owner_and_path_are_checked_before_remote_access():
    connector = Connector()
    owner = SFTPProjectContext("customer_a", "project_1")
    other = SFTPProjectContext("customer_b", "project_1")
    with manager(connector).lease(owner) as session:
        assert session.directory_exists(owner, "/data/customer_a/project_1") is True
        with pytest.raises(PermissionError):
            session.directory_exists(other, "/data/customer_a/project_1")
        with pytest.raises(PermissionError):
            session.directory_exists(owner, "/data/customer_b/project_1")
        with pytest.raises(PermissionError):
            session.directory_exists(owner, "/data/customer_a/project_1/../project_2")
    assert connector.opens == connector.closes == 1


def test_slot_is_released_after_inspection_exception():
    connector = Connector()
    context = SFTPProjectContext("a", "b")
    with pytest.raises(RuntimeError):
        with manager(connector, 1).lease(context):
            raise RuntimeError("inspection failed")
    with manager(connector, 1).lease(context):
        pass
    assert connector.opens == connector.closes == 2


def test_one_slot_blocks_second_thread_until_first_releases():
    connector = Connector()
    sessions = manager(connector, 1)
    context = SFTPProjectContext("a", "b")
    entered = Event()
    finished = Event()

    def second():
        with sessions.lease(context):
            entered.set()
        finished.set()

    with sessions.lease(context):
        thread = Thread(target=second, daemon=True)
        thread.start()
        assert not entered.wait(0.05)
    assert finished.wait(2)
    thread.join(timeout=2)
    assert connector.opens == connector.closes == 2


@pytest.mark.parametrize("path", ["/data/a/b/../../c", "/data/a/other", "/data/a/bad", "/other/a/b"])
def test_path_escape_rejected(path):
    with pytest.raises(PermissionError):
        require_project_sftp_path("/data", "a", "b", path)


def test_invalid_project_context_rejected():
    with pytest.raises(ValueError):
        SFTPProjectContext("../other", "project")
