from contextlib import contextmanager
from hashlib import sha256
from io import BytesIO

from mcm_solarcheck.infrastructure.sqlite_transfer_manifest import SQLiteTransferManifest
from mcm_solarcheck.services.resume_restart_recovery import ResumeRestartRecovery


class Locks:
    def __init__(self):
        self.active = False
        self.calls = 0

    @contextmanager
    def hold(self, *identity):
        assert not self.active
        self.active = True
        self.calls += 1
        try:
            yield
        finally:
            self.active = False


class Remote:
    def __init__(self, data, locks):
        self.data = data
        self.locks = locks

    def read_staging_chunks(self, key, chunk_size):
        assert self.locks.active
        for i in range(0, len(self.data), chunk_size):
            yield self.data[i:i + chunk_size]


def test_restart_inspection_is_read_only_and_lock_guarded(tmp_path):
    path = tmp_path / "manifest.db"
    store = SQLiteTransferManifest(path)
    transfer = store.create("c", "p", "c/p/rgb.jpg", 6, sha256(b"abcdef").hexdigest())
    locks = Locks()
    # A new store instance models reopening durable metadata after restart.
    reopened = SQLiteTransferManifest(path)
    recovery = ResumeRestartRecovery(reopened, Remote(b"abcd", locks), locks=locks, chunk_size=2)
    result = recovery.inspect(transfer, "c", "p", BytesIO(b"abcdef"))
    assert (result.status, result.verified_offset) == ("verified_prefix", 4)
    assert locks.calls == 1
    assert reopened.get(transfer, "c", "p")["state"] == "pending"
