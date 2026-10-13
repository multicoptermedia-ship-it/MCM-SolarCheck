from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal


def test_publication_journal_persists_across_instances(tmp_path):
    database = tmp_path / "journal.db"
    first = SQLitePublicationJournal(database)
    digest = sha256(b"abc").hexdigest()
    first.prepare("transfer", "customer", "project", "final.bin", 3, digest)
    second = SQLitePublicationJournal(database)
    assert second.get("transfer", "customer", "project")["state"] == "prepared"
    assert second.transition("transfer", "customer", "project", "prepared", "publishing")
    assert not first.transition("transfer", "customer", "project", "prepared", "publishing")
    assert first.get("transfer", "customer", "project")["state"] == "publishing"
    assert second.transition("transfer", "customer", "project", "publishing", "published")


def test_conflicting_reuse_of_transfer_is_rejected(tmp_path):
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    digest = sha256(b"abc").hexdigest()
    journal.prepare("transfer", "customer", "project", "final.bin", 3, digest)
    journal.prepare("transfer", "customer", "project", "final.bin", 3, digest)
    with pytest.raises(ValueError):
        journal.prepare("transfer", "other", "project", "final.bin", 3, digest)
    with pytest.raises(ValueError):
        journal.prepare("transfer", "customer", "project", "different.bin", 3, digest)
    assert journal.get("transfer", "other", "project") is None
