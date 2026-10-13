import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations
from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.canonical_reserved_local_publication import CanonicalReservedLocalPublication


class Transfers:
    def get(self, *args):
        return {"state": "pending", "expected_size": 3, "expected_sha256": "a" * 64}


def test_unprovisioned_directory_is_not_created(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    db = tmp_path / "journal.db"
    service = CanonicalReservedLocalPublication(
        root, Transfers(), SQLitePublicationJournal(db), SQLitePublicationDestinations(db)
    )
    with pytest.raises(ValueError):
        service.publish("t", "c", "p", source=tmp_path / ".assembly-a")
    assert not (root / "c").exists()


@pytest.mark.parametrize("bad", ["../escape", "/absolute", "a/b", "", ".", "with space"])
def test_unsafe_transfer_identifier_rejected(tmp_path, bad):
    root = tmp_path / "storage"
    root.mkdir()
    db = tmp_path / "journal.db"
    service = CanonicalReservedLocalPublication(
        root, Transfers(), SQLitePublicationJournal(db), SQLitePublicationDestinations(db)
    )
    with pytest.raises(ValueError):
        service.destination_for(bad, "c", "p")


def test_symlinked_project_directory_is_rejected(tmp_path):
    root = tmp_path / "storage"
    (root / "c").mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "c" / "p").symlink_to(outside, target_is_directory=True)
    db = tmp_path / "journal.db"
    service = CanonicalReservedLocalPublication(
        root, Transfers(), SQLitePublicationJournal(db), SQLitePublicationDestinations(db)
    )
    with pytest.raises(ValueError):
        service.publish("t", "c", "p", source=tmp_path / ".assembly-a")
    assert not (outside / "t.bin").exists()
