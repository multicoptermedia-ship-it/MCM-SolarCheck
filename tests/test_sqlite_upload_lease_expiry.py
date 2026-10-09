import pytest

from mcm_solarcheck.infrastructure.sqlite_upload_leases import SQLiteUploadLeases, UploadLeaseBusy


def test_expired_lease_can_be_reclaimed_and_old_owner_cannot_release(tmp_path, monkeypatch):
    import mcm_solarcheck.infrastructure.sqlite_upload_leases as module

    clock = [1000.0]
    monkeypatch.setattr(module.time, "time", lambda: clock[0])
    leases = SQLiteUploadLeases(tmp_path / "leases.sqlite", lease_seconds=10)
    key, old_token = leases.acquire("c", "p", "a.jpg")
    clock[0] = 1009.0
    with pytest.raises(UploadLeaseBusy):
        leases.acquire("c", "p", "a.jpg")
    clock[0] = 1011.0
    _, new_token = leases.acquire("c", "p", "a.jpg")
    assert not leases.renew(key, old_token)
    assert not leases.release(key, old_token)
    assert leases.renew(key, new_token)
    assert leases.release(key, new_token)
