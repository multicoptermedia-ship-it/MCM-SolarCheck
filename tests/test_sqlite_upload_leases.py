import pytest

from mcm_solarcheck.infrastructure.sqlite_upload_leases import SQLiteUploadLeases, UploadLeaseBusy


def test_competing_clients_and_owner_release(tmp_path):
    db = tmp_path / "leases.sqlite"
    first = SQLiteUploadLeases(db)
    second = SQLiteUploadLeases(db)
    key, token = first.acquire("c", "p", "rgb.jpg")
    with pytest.raises(UploadLeaseBusy):
        second.acquire("c", "p", "rgb.jpg")
    assert not second.release(key, "wrong-token")
    assert first.renew(key, token)
    assert first.release(key, token)
    assert not first.release(key, token)
    assert second.acquire("c", "p", "rgb.jpg")[0] == key


def test_different_files_can_proceed(tmp_path):
    store = SQLiteUploadLeases(tmp_path / "leases.sqlite")
    with store.hold("c", "p", "a.jpg"):
        with store.hold("c", "p", "b.jpg"):
            pass


def test_unsafe_identity_is_rejected(tmp_path):
    store = SQLiteUploadLeases(tmp_path / "leases.sqlite")
    with pytest.raises(ValueError):
        store.acquire("c", "p", "../a.jpg")
