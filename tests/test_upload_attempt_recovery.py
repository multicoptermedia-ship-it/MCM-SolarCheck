"""Interrupted uploads are visible without destructive automatic cleanup."""
from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_attempt_recovery import UploadAttemptRecovery


def test_interrupted_attempt_visible_after_restart(tmp_path):
    database = tmp_path / "attempts.sqlite"
    first = SQLiteUploadAttemptStore(database)
    attempt = first.begin(customer_id="alice", project_id="solar", filename="rgb.jpg")
    recovery = UploadAttemptRecovery(SQLiteUploadAttemptStore(database))
    items = recovery.interrupted()
    assert len(items) == 1
    assert (items[0].attempt_id, items[0].customer_id, items[0].project_id) == (attempt, "alice", "solar")
    assert recovery.interrupted() == items
