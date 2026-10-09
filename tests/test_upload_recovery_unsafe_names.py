from mcm_solarcheck.infrastructure.sqlite_upload_attempts import SQLiteUploadAttemptStore
from mcm_solarcheck.services.upload_attempt_recovery import UploadAttemptRecovery


def test_unsafe_names_do_not_access_files(tmp_path):
    store = SQLiteUploadAttemptStore(tmp_path / "db.sqlite")
    for name in ("../outside", "sub\\file.jpg", "bad\x00name"):
        store.begin(customer_id="c", project_id="p", filename=name)
    def should_not_resolve(*_):
        return tmp_path
    assert [status for _, status in UploadAttemptRecovery(store).inspect(should_not_resolve)] == ["unsafe"] * 3
