"""Isolated tests for transactional recovery auditing; no MariaDB connection."""
from datetime import datetime, timedelta, timezone

from mcm_solarcheck.infrastructure.mariadb_audited_recovery import MariaDBAuditedRecovery
from mcm_solarcheck.services.mariadb_recovery_authorization import QuiescenceProof


TOKEN = "a" * 32
PROOF = QuiescenceProof(9, 1, TOKEN, "operator", "verified-shutdown-123")


class Cursor:
    def __init__(self, *, fail_at=None, row=None):
        self.calls = []
        self.rowcount = 1
        self.fail_at = fail_at
        self.row = row
        self.closed = False

    def execute(self, sql, params):
        self.calls.append((sql, params))
        self.rowcount = 0 if len(self.calls) == self.fail_at else 1

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


def expired_row():
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=5)
    return (1, 9, TOKEN, past, "worker", TOKEN, past, "running")


def test_success_audits_in_same_transaction_without_token():
    conn = Connection(Cursor(row=expired_row()))
    assert MariaDBAuditedRecovery(lambda: conn, lambda p: True).recover(PROOF) is True
    assert conn.committed and not conn.rolled_back and conn.closed and conn.c.closed
    assert len(conn.c.calls) == 4
    audit_sql, audit_args = conn.c.calls[-1]
    assert "mcm_recovery_audit" in audit_sql
    assert audit_args == (9, 1, "operator", "verified-shutdown-123", "requeued")
    assert TOKEN not in audit_args


def test_failed_audit_rolls_back_recovery():
    conn = Connection(Cursor(row=expired_row(), fail_at=4))
    assert MariaDBAuditedRecovery(lambda: conn, lambda p: True).recover(PROOF) is False
    assert conn.rolled_back and not conn.committed and conn.closed


def test_stale_pair_cannot_write_success_audit():
    conn = Connection(Cursor(row=None))
    assert MariaDBAuditedRecovery(lambda: conn, lambda p: True).recover(PROOF) is False
    assert len(conn.c.calls) == 1
    assert conn.rolled_back


def test_denied_quiescence_never_connects():
    called = []
    assert MariaDBAuditedRecovery(lambda: called.append(True), lambda p: False).recover(PROOF) is False
    assert not called
