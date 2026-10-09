import time

from mcm_solarcheck.infrastructure.sqlite_upload_leases import SQLiteUploadLeases


def test_active_lease_is_renewed(tmp_path):
    store = SQLiteUploadLeases(tmp_path / "db.sqlite", lease_seconds=0.3)
    with store.hold("customer", "project", "image.jpg"):
        time.sleep(0.65)
        from mcm_solarcheck.infrastructure.sqlite_upload_leases import UploadLeaseBusy
        import pytest
        with pytest.raises(UploadLeaseBusy):
            store.acquire("customer", "project", "image.jpg")
    key, token = store.acquire("customer", "project", "image.jpg")
    assert store.release(key, token)
