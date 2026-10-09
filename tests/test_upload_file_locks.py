from hashlib import sha256
from threading import Event, Thread

import pytest

from mcm_solarcheck.infrastructure.upload_file_locks import UploadFileLocks
from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_reconciliation import UploadReconciliation


def test_lock_identity_rejects_traversal(tmp_path):
    locks = UploadFileLocks(tmp_path / "locks")
    with pytest.raises(ValueError):
        with locks.hold("c", "p", "../image.jpg"):
            pass


def test_reconciliation_uses_shared_lock(tmp_path):
    locks = UploadFileLocks(tmp_path / "locks")
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    payload = b"abc"
    store.begin(customer_id="c", project_id="p", filename="image.jpg",
                expected_size=3, expected_sha256=sha256(payload).hexdigest())
    (tmp_path / "image.jpg").write_bytes(payload)
    entered = Event()
    finished = Event()

    def worker():
        entered.set()
        UploadReconciliation(store, file_locks=locks).run_once(lambda *_: tmp_path)
        finished.set()

    with locks.hold("c", "p", "image.jpg"):
        thread = Thread(target=worker)
        thread.start()
        assert entered.wait(2)
        assert not finished.wait(0.1)
    thread.join(3)
    assert finished.is_set()
    assert store.pending() == []
