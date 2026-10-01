import sqlite3

from mcm_solarcheck.infrastructure.sqlite_sepa import SQLiteSepaMandateStore
from mcm_solarcheck.services.sepa import SepaMandate, SepaMandateStatus


def test_sepa_mandate_persists_without_bank_account_data(tmp_path) -> None:
    database = tmp_path / "sepa.sqlite"
    store = SQLiteSepaMandateStore(database)
    store.create(SepaMandate("mandate-a", "user-a", "provider-a"))

    active = store.activate(
        "mandate-a", "user-a", "provider-mandate-a"
    )

    assert active.status is SepaMandateStatus.ACTIVE
    assert SQLiteSepaMandateStore(database).get("mandate-a") == active


def test_sepa_mandate_is_owner_guarded(tmp_path) -> None:
    store = SQLiteSepaMandateStore(tmp_path / "sepa.sqlite")
    store.create(SepaMandate("mandate-a", "user-a", "provider-a"))

    try:
        store.activate("mandate-a", "user-b", "provider-mandate-a")
    except PermissionError:
        pass
    else:
        raise AssertionError("cross-user mandate activation must fail")


def test_sepa_mandate_storage_contains_no_bank_account_or_customer_data(tmp_path) -> None:
    database = tmp_path / "sepa.sqlite"
    SQLiteSepaMandateStore(database)

    with sqlite3.connect(database) as connection:
        columns = [
            row[1]
            for row in connection.execute("PRAGMA table_info(sepa_mandates)")
        ]

    assert columns == [
        "mandate_id",
        "user_id",
        "provider_id",
        "provider_reference",
        "status",
    ]
