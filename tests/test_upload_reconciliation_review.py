from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_reconciliation import UploadReconciliation


def test_missing_and_legacy_uploads_require_review(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    store.begin(customer_id="c", project_id="p", filename="missing.jpg")
    store.begin(customer_id="c", project_id="p", filename="legacy.jpg")
    (tmp_path / "legacy.jpg").write_bytes(b"old")
    outcomes = {r.outcome for r in UploadReconciliation(store).run_once(lambda *_: tmp_path)}
    assert outcomes == {"review_file_absent", "review_file_present_unverified"}
    assert len(store.pending()) == 2


def test_symlink_is_not_auto_finalized(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    store.begin(customer_id="c", project_id="p", filename="image.jpg",
                expected_size=3, expected_sha256="a" * 64)
    outside = tmp_path / "outside"
    outside.write_bytes(b"abc")
    (tmp_path / "image.jpg").symlink_to(outside)
    assert UploadReconciliation(store).run_once(lambda *_: tmp_path)[0].outcome == "review_unsafe"
    assert len(store.pending()) == 1
    assert outside.read_bytes() == b"abc"
