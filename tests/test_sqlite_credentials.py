from __future__ import annotations

import sqlite3

import pytest

from mcm_solarcheck.infrastructure.sqlite_credentials import SQLiteCredentialStore
from mcm_solarcheck.services.online_credentials import PasswordCredentialService


def test_sqlite_credentials_round_trip_password_proof(tmp_path) -> None:
    database = tmp_path / "online.sqlite"
    store = SQLiteCredentialStore(database)
    service = PasswordCredentialService(store)

    service.set_password("user-1", "correct horse battery staple")

    assert service.verify_password("user-1", "correct horse battery staple")
    assert not service.verify_password("user-1", "different password value")


def test_sqlite_credentials_do_not_persist_plaintext_password(tmp_path) -> None:
    database = tmp_path / "online.sqlite"
    store = SQLiteCredentialStore(database)
    service = PasswordCredentialService(store)
    password = "correct horse battery staple"

    service.set_password("user-1", password)

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT user_id, salt_hex, digest_hex, iterations FROM online_credentials"
        ).fetchone()
    assert row[0] == "user-1"
    assert password not in row
    assert row[1]
    assert row[2]
    assert row[3] > 0


def test_sqlite_credentials_raise_for_unknown_identity(tmp_path) -> None:
    store = SQLiteCredentialStore(tmp_path / "online.sqlite")

    with pytest.raises(KeyError):
        store.get("missing")
