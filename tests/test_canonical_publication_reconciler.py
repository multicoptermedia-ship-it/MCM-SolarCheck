import os
from hashlib import sha256

import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_journal import SQLitePublicationJournal
from mcm_solarcheck.services.canonical_publication_reconciler import CanonicalPublicationReconciler


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_published_journal_does_not_bypass_fresh_hash_verification(tmp_path):
    root = tmp_path / "storage"
    project = root / "customer" / "project"
    project.mkdir(parents=True)
    final = project / "transfer.bin"
    final.write_bytes(b"abc")
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    digest = sha256(b"abc").hexdigest()
    journal.prepare("transfer", "customer", "project", str(final), 3, digest)
    assert journal.transition("transfer", "customer", "project", "prepared", "publishing")
    assert journal.transition("transfer", "customer", "project", "publishing", "published")
    reconciler = CanonicalPublicationReconciler(journal, root)
    assert reconciler.inspect("transfer", "customer", "project") == "verified_final"
    final.write_bytes(b"bad")
    assert reconciler.inspect("transfer", "customer", "project") == "invalid_final"
    final.unlink()
    assert reconciler.inspect("transfer", "customer", "project") == "missing_final"


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_journal_destination_mismatch_is_rejected(tmp_path):
    root = tmp_path / "storage"
    (root / "customer" / "project").mkdir(parents=True)
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    journal.prepare("transfer", "customer", "project", str(tmp_path / "elsewhere.bin"),
                    3, sha256(b"abc").hexdigest())
    assert CanonicalPublicationReconciler(journal, root).inspect(
        "transfer", "customer", "project"
    ) == "invalid_destination"


@pytest.mark.skipif(os.name != "posix", reason="POSIX required")
def test_symlinked_parent_is_unavailable(tmp_path):
    root = tmp_path / "storage"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "customer").symlink_to(outside, target_is_directory=True)
    journal = SQLitePublicationJournal(tmp_path / "journal.db")
    final = root / "customer" / "project" / "transfer.bin"
    journal.prepare("transfer", "customer", "project", str(final), 3, sha256(b"abc").hexdigest())
    assert CanonicalPublicationReconciler(journal, root).inspect(
        "transfer", "customer", "project"
    ) == "unavailable"
