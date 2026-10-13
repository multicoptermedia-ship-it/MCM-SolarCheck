import pytest

from mcm_solarcheck.infrastructure.mariadb_job_lease_adapter import MariaDBJobLeaseAdapter


class Cursor:
    def __init__(self, rowcount=1, error=None):
        self.rowcount = rowcount
        self.error = error
        self.sql = None
        self.params = None
        self.closed = False

    def execute(self, sql, params):
        self.sql, self.params = sql, params
        if self.error:
            raise self.error

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, cursor):
        self.test_cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.test_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_claim_is_parameterized_committed_and_closed():
    conn = Connection(Cursor())
    adapter = MariaDBJobLeaseAdapter(lambda: conn)
    token = adapter.claim(42, "worker", lease_seconds=30)
    assert isinstance(token, str) and len(token) == 32
    assert conn.test_cursor.params == ("worker", token, 30, 42)
    assert conn.committed and conn.closed and conn.test_cursor.closed
    assert not conn.rolled_back


def test_stale_update_does_not_succeed():
    conn = Connection(Cursor(rowcount=0))
    adapter = MariaDBJobLeaseAdapter(lambda: conn)
    assert adapter.complete(42, "worker", "a" * 32) is False
    assert conn.committed and conn.closed


def test_driver_error_rolls_back_and_closes():
    conn = Connection(Cursor(error=RuntimeError("db error")))
    adapter = MariaDBJobLeaseAdapter(lambda: conn)
    with pytest.raises(RuntimeError, match="db error"):
        adapter.renew(42, "worker", "a" * 32)
    assert conn.rolled_back and conn.closed and conn.test_cursor.closed
    assert not conn.committed


def test_invalid_input_prevents_connection():
    calls = []
    adapter = MariaDBJobLeaseAdapter(lambda: calls.append("connected"))
    with pytest.raises(ValueError):
        adapter.claim(0, "worker")
    with pytest.raises(ValueError):
        adapter.renew(1, "worker", "bad")
    assert calls == []
