import pytest

from mcm_solarcheck.infrastructure.sqlite_upload_leases import SQLiteUploadLeases, UploadLeaseLost


def test_lost_lease_is_reported_at_context_exit(tmp_path):
    store = SQLiteUploadLeases(tmp_path / "db.sqlite", lease_seconds=60)
    with pytest.raises(UploadLeaseLost):
        with store.hold("c", "p", "image.jpg"):
            with __import__("sqlite3").connect(store.database) as db:
                db.execute("DELETE FROM upload_file_leases")
    assert store.acquire("c", "p", "image.jpg")


def test_lease_released_on_body_exception(tmp_path):
    store = SQLiteUploadLeases(tmp_path / "db.sqlite")
    with pytest.raises(RuntimeError):
        with store.hold("c", "p", "image.jpg"):
            raise RuntimeError("upload failed")
    key, token = store.acquire("c", "p", "image.jpg")
    assert store.release(key, token)
