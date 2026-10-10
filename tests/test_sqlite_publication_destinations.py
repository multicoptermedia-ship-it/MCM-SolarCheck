import pytest

from mcm_solarcheck.infrastructure.sqlite_publication_destinations import SQLitePublicationDestinations


def test_destination_reservation_is_persistent_and_idempotent(tmp_path):
    database = tmp_path / "reservations.db"
    first = SQLitePublicationDestinations(database)
    assert first.reserve("/private/a.bin", "t1", "c1", "p1")
    second = SQLitePublicationDestinations(database)
    assert second.reserve("/private/a.bin", "t1", "c1", "p1")
    assert second.lookup("/private/a.bin") == ("t1", "c1", "p1")


def test_destination_and_transfer_conflicts_are_rejected(tmp_path):
    store = SQLitePublicationDestinations(tmp_path / "reservations.db")
    store.reserve("/private/a.bin", "t1", "c1", "p1")
    with pytest.raises(ValueError):
        store.reserve("/private/a.bin", "t2", "c2", "p2")
    with pytest.raises(ValueError):
        store.reserve("/private/b.bin", "t1", "c1", "p1")
    assert store.lookup("/private/b.bin") is None
