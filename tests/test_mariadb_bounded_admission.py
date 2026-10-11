import pytest

from mcm_solarcheck.infrastructure.mariadb_staging_migrations import (
    MIGRATIONS, MIGRATION_TABLE_SQL, pending_migrations,
)
from mcm_solarcheck.infrastructure.mariadb_processing_slot_sql import select_free_slot
from mcm_solarcheck.infrastructure.mariadb_bounded_job_admission import MariaDBBoundedJobAdmission


class Cursor:
    def __init__(self, rows, rowcounts):
        self.rows = rows
        self.rowcounts = iter(rowcounts)
        self.rowcount = 0
        self.executed = []
        self.closed = False

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if params is not None:
            self.rowcount = next(self.rowcounts)

    def fetchall(self):
        return self.rows

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


def test_migration_plan_is_versioned_and_pure():
    assert [m.version for m in MIGRATIONS] == [1, 2, 3]
    assert "mcm_schema_migrations" in MIGRATION_TABLE_SQL
    assert len(pending_migrations([])) == 3
    assert [m.version for m in pending_migrations([1])] == [2, 3]
    assert [m.version for m in pending_migrations([1, 2])] == [3]
    assert pending_migrations([1, 2, 3]) == ()
    with pytest.raises(ValueError):
        pending_migrations([2])


def test_slot_selection_fails_closed():
    assert select_free_slot([(1, None, None), (2, 8, None)]) == 1
    assert select_free_slot([(1, 7, None), (2, 8, None)]) is None
    with pytest.raises(ValueError):
        select_free_slot([(1, None, None)])


def test_admission_commits_both_updates():
    conn = Connection(Cursor([(1, None, None), (2, None, None)], [1, 1]))
    result = MariaDBBoundedJobAdmission(lambda: conn).claim(17, "worker")
    assert result[0] == 1 and len(result[1]) == 32
    assert conn.committed and conn.closed and conn.test_cursor.closed
    assert len(conn.test_cursor.executed) == 3


def test_no_slot_rolls_back_without_job_claim():
    conn = Connection(Cursor([(1, 5, None), (2, 6, None)], []))
    assert MariaDBBoundedJobAdmission(lambda: conn).claim(17, "worker") is None
    assert conn.rolled_back and not conn.committed
    assert len(conn.test_cursor.executed) == 1


def test_failed_job_claim_rolls_back_slot():
    conn = Connection(Cursor([(1, None, None), (2, 6, None)], [1, 0]))
    assert MariaDBBoundedJobAdmission(lambda: conn).claim(17, "worker") is None
    assert conn.rolled_back and not conn.committed


def test_driver_error_rolls_back():
    conn = Connection(Cursor([(1, None, None), (2, 6, None)], []))
    with pytest.raises(StopIteration):
        MariaDBBoundedJobAdmission(lambda: conn).claim(17, "worker")
    assert conn.rolled_back and conn.closed
