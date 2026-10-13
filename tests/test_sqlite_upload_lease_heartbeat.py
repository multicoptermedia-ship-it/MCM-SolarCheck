import time

import pytest

from mcm_solarcheck.infrastructure.sqlite_upload_leases import (
    SQLiteUploadLeases,
    UploadLeaseBusy,
)


def test_active_lease_is_renewed(tmp_path):
    # Allow substantial scheduling slack on loaded CI runners.
    store = SQLiteUploadLeases(tmp_path / "db.sqlite", lease_seconds=3.0)
    with store.hold("customer", "project", "image.jpg"):
        time.sleep(1.4)
        key = store._key("customer", "project", "image.jpg")
        with __import__("sqlite3").connect(store.database) as db:
            expiry = db.execute(
                "SELECT expires_at FROM upload_file_leases WHERE lock_key=?", (key,)
            ).fetchone()[0]
        assert expiry > time.time() + 2.0
        with pytest.raises(UploadLeaseBusy):
            store.acquire("customer", "project", "image.jpg")
    key, token = store.acquire("customer", "project", "image.jpg")
    assert store.release(key, token)
