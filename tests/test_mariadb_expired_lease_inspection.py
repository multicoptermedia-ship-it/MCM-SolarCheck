from datetime import datetime, timedelta

import pytest

from mcm_solarcheck.infrastructure.mariadb_expired_lease_inspection import classify_expired_pair
from mcm_solarcheck.infrastructure.mariadb_expired_lease_inspector import MariaDBExpiredLeaseInspector
from mcm_solarcheck.services.mariadb_recovery_advice import advise_mariadb_recovery


NOW = datetime(2026, 1, 1, 12, 0, 0)


def pair(slot_expiry, job_expiry, *, token="a" * 32, job_token=None, state="running"):
    return (1, 9, token, slot_expiry, "worker", token if job_token is None else job_token, job_expiry, state)


def test_pair_states():
    past = NOW - timedelta(seconds=1)
    future = NOW + timedelta(seconds=1)
    assert classify_expired_pair(None, NOW) == "empty"
    assert classify_expired_pair(pair(future, future), NOW) == "active"
    assert classify_expired_pair(pair(past, past), NOW) == "expired_requires_quiescence"
    assert classify_expired_pair(pair(past, future), NOW) == "manual_review"
    assert classify_expired_pair(pair(past, past, job_token="b" * 32), NOW) == "manual_review"


def test_advice_never_authorizes_reassignment():
    for state in ("empty", "active", "expired_requires_quiescence", "manual_review"):
        assert advise_mariadb_recovery(state).may_reassign is False
    with pytest.raises(ValueError):
        advise_mariadb_recovery("ready")


class Cursor:
    def __init__(self, row):
        self.row = row
        self.closed = False
        self.args = None

    def execute(self, sql, args):
        self.args = args

    def fetchone(self):
        return self.row

    def close(self):
        self.closed = True


class Connection:
    def __init__(self, row):
        self.c = Cursor(row)
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.c

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed = True


def test_inspection_is_read_only_and_closes_connection():
    conn = Connection(pair(NOW - timedelta(seconds=1), NOW - timedelta(seconds=1)))
    status = MariaDBExpiredLeaseInspector(lambda: conn).inspect(1, now=NOW)
    assert status == "expired_requires_quiescence"
    assert conn.c.args == (1,)
    assert conn.rolled_back and conn.closed and conn.c.closed


def test_invalid_slot_never_connects():
    calls = []
    with pytest.raises(ValueError):
        MariaDBExpiredLeaseInspector(lambda: calls.append(1)).inspect(3, now=NOW)
    assert calls == []
