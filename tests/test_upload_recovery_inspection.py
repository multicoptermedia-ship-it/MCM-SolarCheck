from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_attempt_recovery import UploadAttemptRecovery


def test_inspection_is_read_only(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    attempt = store.begin(customer_id="c", project_id="p", filename="rgb.jpg")
    directory = tmp_path / "uploads" / "c" / "p"
    directory.mkdir(parents=True)
    recovery = UploadAttemptRecovery(store)
    assert recovery.inspect(lambda *_: directory)[0][1] == "file_absent"
    (directory / "rgb.jpg").write_bytes(b"original")
    assert recovery.inspect(lambda *_: directory)[0][1] == "file_present_unverified"
    assert (directory / "rgb.jpg").read_bytes() == b"original"
    assert recovery.interrupted()[0].attempt_id == attempt


def test_symlink_is_not_trusted(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    store.begin(customer_id="c", project_id="p", filename="rgb.jpg")
    directory = tmp_path / "uploads"
    directory.mkdir()
    target = tmp_path / "outside"
    target.write_bytes(b"private")
    (directory / "rgb.jpg").symlink_to(target)
    assert UploadAttemptRecovery(store).inspect(lambda *_: directory)[0][1] == "unsafe"
    assert target.read_bytes() == b"private"
