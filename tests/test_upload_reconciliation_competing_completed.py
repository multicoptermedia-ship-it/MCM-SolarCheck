from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_reconciliation import UploadReconciliation


def test_previous_completed_attempt_blocks_ambiguous_recovery(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    digest = sha256(b"abc").hexdigest()
    first = store.begin(customer_id="c", project_id="p", filename="image.jpg",
                        expected_size=3, expected_sha256=digest)
    store.finish(first, succeeded=True)
    store.begin(customer_id="c", project_id="p", filename="image.jpg",
                expected_size=3, expected_sha256=digest)
    (tmp_path / "image.jpg").write_bytes(b"abc")
    assert UploadReconciliation(store).run_once(lambda *_: tmp_path)[0].outcome == "review_conflict"
    assert len(store.pending()) == 1
