import pytest

from mcm_solarcheck.infrastructure.sqlite_resume_locks import SQLiteResumeLocks
from mcm_solarcheck.infrastructure.sqlite_upload_leases import UploadLeaseBusy


def test_resume_lock_excludes_competing_process_instances(tmp_path):
    database = tmp_path / "shared.db"
    first = SQLiteResumeLocks(database, lease_seconds=10)
    second = SQLiteResumeLocks(database, lease_seconds=10)
    with first.hold("c", "p", "transfer"):
        with pytest.raises(UploadLeaseBusy):
            with second.hold("c", "p", "transfer"):
                pass
        # Other transfers are independent.
        with second.hold("c", "p", "other"):
            pass
    with second.hold("c", "p", "transfer"):
        pass


def test_resume_lock_rejects_invalid_transfer_identity(tmp_path):
    locks = SQLiteResumeLocks(tmp_path / "shared.db")
    with pytest.raises(ValueError):
        with locks.hold("c", "p", "../unsafe"):
            pass
