"""Durable upload attempt journal behavior."""
import pytest
from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore


def test_pending_survives_new_store_instance(tmp_path):
    database = tmp_path / "attempts.sqlite"
    store = SQLiteUploadAttemptStore(database)
    attempt = store.begin(customer_id="alice", project_id="p", filename="image.tiff")
    reopened = SQLiteUploadAttemptStore(database)
    assert reopened.pending() == [(attempt, "alice", "p", "image.tiff")]
    reopened.finish(attempt, succeeded=True)
    assert store.pending() == []


def test_failed_attempt_is_not_pending(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "attempts.sqlite")
    attempt = store.begin(customer_id="alice", project_id="p", filename="image.tiff")
    store.finish(attempt, succeeded=False)
    assert store.pending() == []
    with pytest.raises(ValueError):
        store.finish(attempt, succeeded=True)


def test_rejects_empty_identity(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "attempts.sqlite")
    with pytest.raises(ValueError):
        store.begin(customer_id="", project_id="p", filename="x")
