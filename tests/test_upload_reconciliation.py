from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_reconciliation import UploadReconciliation


def test_verified_upload_finalized_once(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    payload = b"rgb-payload"
    attempt = store.begin(customer_id="c", project_id="p", filename="image.jpg",
                          expected_size=len(payload), expected_sha256=sha256(payload).hexdigest())
    (tmp_path / "image.jpg").write_bytes(payload)
    reconcile = UploadReconciliation(store)
    assert [(r.attempt_id, r.outcome) for r in reconcile.run_once(lambda *_: tmp_path)] == [(attempt, "completed")]
    assert reconcile.run_once(lambda *_: tmp_path) == []
    assert (tmp_path / "image.jpg").read_bytes() == payload


def test_mismatched_file_remains_pending(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    store.begin(customer_id="c", project_id="p", filename="image.jpg",
                expected_size=3, expected_sha256=sha256(b"abc").hexdigest())
    (tmp_path / "image.jpg").write_bytes(b"xyz")
    assert UploadReconciliation(store).run_once(lambda *_: tmp_path)[0].outcome == "review_hash_mismatch"
    assert len(store.pending()) == 1


def test_competing_pending_uploads_not_auto_finalized(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    for _ in range(2):
        store.begin(customer_id="c", project_id="p", filename="image.jpg",
                    expected_size=3, expected_sha256=sha256(b"abc").hexdigest())
    (tmp_path / "image.jpg").write_bytes(b"abc")
    assert [r.outcome for r in UploadReconciliation(store).run_once(lambda *_: tmp_path)] == ["review_conflict"] * 2
    assert len(store.pending()) == 2
