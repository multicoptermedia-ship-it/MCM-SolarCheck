from datetime import datetime, timedelta

import pytest

from mcm_solarcheck.infrastructure.mariadb_authorized_recovery import MariaDBAuthorizedRecovery
from mcm_solarcheck.services.mariadb_recovery_authorization import QuiescenceProof


class Cursor:
    def __init__(self, row, counts=(1, 1)):
        self.row = row
        self.counts = iter(counts)
        self.rowcount = 0
        self.calls = []
        self.closed = False

    def execute(self, sql, args):
        self.calls.append((sql, args))
        if len(self.calls) > 1:
            self.rowcount = next(self.counts)

    def fetchone(self):
        return self.row

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


TOKEN = "a" * 32
PROOF = QuiescenceProof(9, 1, TOKEN, "operator", "verified-worker-shutdown-123")


def expired_row():
    past = datetime.utcnow() - timedelta(minutes=2)
    return (1, 9, TOKEN, past, "worker", TOKEN, past, "running")


def test_proof_rejects_bad_scope():
    with pytest.raises(ValueError):
        QuiescenceProof(9, 3, TOKEN, "operator", "evidence")
    with pytest.raises(ValueError):
        QuiescenceProof(9, 1, "bad", "operator", "evidence")


def test_denied_verification_never_connects():
    calls = []
    service = MariaDBAuthorizedRecovery(lambda: calls.append(1), lambda proof: False)
    assert service.recover(PROOF) is False
    assert calls == []


def test_recovery_commits_both_updates():
    conn = Connection(Cursor(expired_row()))
    service = MariaDBAuthorizedRecovery(lambda: conn, lambda proof: True)
    assert service.recover(PROOF) is True
    assert conn.committed and conn.closed and conn.c.closed
    assert len(conn.c.calls) == 3


def test_second_update_failure_rolls_back():
    conn = Connection(Cursor(expired_row(), counts=(1, 0)))
    service = MariaDBAuthorizedRecovery(lambda: conn, lambda proof: True)
    assert service.recover(PROOF) is False
    assert conn.rolled_back and not conn.committed


def test_repeated_recovery_rejected():
    conn = Connection(Cursor(None))
    service = MariaDBAuthorizedRecovery(lambda: conn, lambda proof: True)
    assert service.recover(PROOF) is False
    assert conn.rolled_back and not conn.committed
