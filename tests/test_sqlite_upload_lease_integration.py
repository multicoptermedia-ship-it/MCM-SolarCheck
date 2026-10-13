from hashlib import sha256

from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.infrastructure.sqlite_upload_leases import SQLiteUploadLeases
from mcm_solarcheck.services.upload_reconciliation import UploadReconciliation


def test_reconciliation_accepts_sqlite_coordinator(tmp_path):
    db = tmp_path / "state.sqlite"
    attempts = SQLiteUploadAttemptStore(db)
    locks = SQLiteUploadLeases(db)
    data = b"abc"
    attempts.begin(customer_id="c", project_id="p", filename="image.jpg",
                   expected_size=3, expected_sha256=sha256(data).hexdigest())
    (tmp_path / "image.jpg").write_bytes(data)
    results = UploadReconciliation(attempts, file_locks=locks).run_once(lambda *_: tmp_path)
    assert [result.outcome for result in results] == ["completed"]
    assert attempts.pending() == []


def test_upload_and_reconciliation_share_hold_interface(tmp_path):
    from mcm_solarcheck.infrastructure.filesystem_project_upload import FileSystemProjectUploadStore
    from mcm_solarcheck.services.project_upload import ProjectUploadRequest, ValidatedProjectUpload

    locks = SQLiteUploadLeases(tmp_path / "coordination.sqlite")
    store = FileSystemProjectUploadStore(tmp_path / "uploads", file_locks=locks)
    request = ProjectUploadRequest("c", "p", "rgb.jpg", "image/jpeg", b"\xff\xd8\xffabc")
    store.store(ValidatedProjectUpload(request, len(request.content), sha256(request.content).hexdigest()))
    assert (tmp_path / "uploads" / "c" / "p" / "rgb.jpg").read_bytes() == request.content
