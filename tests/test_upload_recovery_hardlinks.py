from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_attempt_recovery import UploadAttemptRecovery


def test_hardlinked_file_requires_review(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    payload = b"abc"
    store.begin(customer_id="c", project_id="p", filename="image.jpg",
                expected_size=len(payload), expected_sha256=sha256(payload).hexdigest())
    original = tmp_path / "original"
    original.write_bytes(payload)
    (tmp_path / "image.jpg").hardlink_to(original)
    assert UploadAttemptRecovery(store).inspect_integrity(lambda *_: tmp_path)[0][1] == "unsafe"
    assert original.read_bytes() == payload
