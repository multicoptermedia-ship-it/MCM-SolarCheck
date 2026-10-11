import pytest

from mcm_solarcheck.infrastructure.mariadb_bounded_job_lifecycle import MariaDBBoundedJobLifecycle


class Cursor:
    def __init__(self, owner=(1,), counts=(1, 1), error=None):
        self.owner = owner
        self.counts = iter(counts)
        self.error = error
        self.rowcount = 0
        self.calls = []
        self.closed = False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        if self.error:
            raise self.error
        if len(self.calls) > 1:
            self.rowcount = next(self.counts)

    def fetchone(self):
        return self.owner

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, cursor):
        self.c = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.c

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


@pytest.mark.parametrize("operation", ["renew", "complete"])
def test_paired_lifecycle_commits(operation):
    connection = Connection(Cursor())
    service = MariaDBBoundedJobLifecycle(lambda: connection)
    if operation == "renew":
        result = service.renew(9, "worker", 1, "a" * 32)
    else:
        result = service.complete(9, "worker", 1, "a" * 32)
    assert result is True
    assert connection.committed and connection.closed and connection.c.closed
    assert len(connection.c.calls) == 3


def test_lost_ownership_fails_without_updates():
    connection = Connection(Cursor(owner=None))
    assert MariaDBBoundedJobLifecycle(lambda: connection).complete(9, "worker", 1, "a" * 32) is False
    assert connection.rolled_back and not connection.committed
    assert len(connection.c.calls) == 1


def test_second_update_failure_rolls_back_first():
    connection = Connection(Cursor(counts=(1, 0)))
    assert MariaDBBoundedJobLifecycle(lambda: connection).renew(9, "worker", 1, "a" * 32) is False
    assert connection.rolled_back and not connection.committed


def test_exception_rolls_back_and_closes():
    connection = Connection(Cursor(error=RuntimeError("simulated")))
    with pytest.raises(RuntimeError, match="simulated"):
        MariaDBBoundedJobLifecycle(lambda: connection).complete(9, "worker", 1, "a" * 32)
    assert connection.rolled_back and connection.closed and connection.c.closed


def test_invalid_identity_does_not_connect():
    called = []
    service = MariaDBBoundedJobLifecycle(lambda: called.append(1))
    with pytest.raises(ValueError):
        service.renew(9, "worker", 3, "a" * 32)
    assert not called
