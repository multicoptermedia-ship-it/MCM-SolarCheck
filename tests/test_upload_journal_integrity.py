from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_attempt_recovery import UploadAttemptRecovery


def test_integrity_verification_and_mismatch(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "state.db")
    payload = b"solarcheck-rgb"
    store.begin(customer_id="c", project_id="p", filename="rgb.jpg",
                expected_size=len(payload), expected_sha256=sha256(payload).hexdigest())
    folder = tmp_path / "uploads"
    folder.mkdir()
    recovery = UploadAttemptRecovery(store)
    assert recovery.inspect_integrity(lambda *_: folder)[0][1] == "file_absent"
    image = folder / "rgb.jpg"
    image.write_bytes(payload)
    assert recovery.inspect_integrity(lambda *_: folder)[0][1] == "verified"
    image.write_bytes(b"short")
    assert recovery.inspect_integrity(lambda *_: folder)[0][1] == "size_mismatch"
    image.write_bytes(b"x" * len(payload))
    assert recovery.inspect_integrity(lambda *_: folder)[0][1] == "hash_mismatch"


def test_legacy_pending_record_remains_unverified(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "state.db")
    store.begin(customer_id="c", project_id="p", filename="rgb.jpg")
    (tmp_path / "rgb.jpg").write_bytes(b"unverified")
    assert UploadAttemptRecovery(store).inspect_integrity(lambda *_: tmp_path)[0][1] == "file_present_unverified"
