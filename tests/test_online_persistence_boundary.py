from __future__ import annotations

from typing import get_type_hints

from mcm_solarcheck.infrastructure.online_persistence import OnlinePersistence


def test_online_persistence_container_has_no_sqlite_specific_type_contract() -> None:
    hints = get_type_hints(OnlinePersistence)

    sqlite_bound = [
        name
        for name, annotation in hints.items()
        if "SQLite" in getattr(annotation, "__name__", str(annotation))
    ]

    assert sqlite_bound == []
