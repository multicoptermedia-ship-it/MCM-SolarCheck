"""Counter/migration and online ownership tests without real project data."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import sqlite3

import pytest

from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase, SCHEMA_VERSION


def profile(anlage="Anlage Nord"):
    return ProjectProfile(
        "Testkunde", anlage, "Weg 1", "12345", "Musterstadt",
        "Inspektor", site_timezone="Europe/Berlin",
    )


def test_offline_sequence_is_immutable_and_independent_of_internal_id(tmp_path):
    db = ProjectDatabase(tmp_path / "pilot.sqlite3")
    db.initialize()
    svc = ProjectApplicationService(db)
    first = svc.create_numbered_offline_project(profile("Norddach"))
    second = svc.create_numbered_offline_project(profile("Suedanlage"))
    assert first.project_id.startswith("sc-") and first.project_id != second.project_id
    assert (first.display_number, second.display_number) == ("SC-0001", "SC-0002")
    assert svc.project_profile(first.project_id).site_name == "Norddach"
    assert db.project_display_number(first.project_id) == "SC-0001"
    assert db.project_display_number(second.project_id) == "SC-0002"
    assert db.project_display_number(second.project_id, customer_id="user-a") is None


def test_online_owner_isolation_and_concurrent_numbering(tmp_path):
    db = ProjectDatabase(tmp_path / "online.sqlite3")
    db.initialize()

    def save(customer):
        return db.create_numbered_project(
            "PV-Anlage", customer_id=customer,
            capacity_kwp=Decimal("21.8"),
        )

    with ThreadPoolExecutor(max_workers=5) as pool:
        result = list(pool.map(save, ["A", "A", "B", "A", "B"]))
    assert sorted(v[1] for v in result if db.project_belongs_to_customer("A", v[0])) == [
        "SC-0001", "SC-0002", "SC-0003",
    ]
    assert sorted(v[1] for v in result if db.project_belongs_to_customer("B", v[0])) == [
        "SC-0001", "SC-0002",
    ]
    for internal_id, _label in result:
        assert not internal_id.startswith("SC-")
        assert db.project_display_number(internal_id, customer_id="not-owner") is None
    assert sorted(p.display_number for p in db.projects_for_customer("A")) == [
        "SC-0001", "SC-0002", "SC-0003",
    ]


def test_legacy_migration_keeps_existing_project_id_and_data(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    db = ProjectDatabase(path)
    db.initialize()
    db.create_project("LEGACY", "Dach Alt")
    with db.connect() as conn:
        conn.execute("DROP TABLE project_display_numbers")
        conn.execute("DROP TABLE project_number_counters")
        conn.execute("UPDATE schema_info SET version=19")
    db.initialize()
    with db.connect() as conn:
        assert conn.execute("SELECT version FROM schema_info").fetchone()[0] == SCHEMA_VERSION
        assert conn.execute("SELECT name FROM projects WHERE project_id='LEGACY'").fetchone()[0] == "Dach Alt"
    assert db.project_display_number("LEGACY") == "SC-0001"
    fresh = ProjectApplicationService(db).create_numbered_offline_project(profile())
    assert fresh.display_number == "SC-0002"


def test_bad_name_never_commits_number(tmp_path):
    db = ProjectDatabase(tmp_path / "bad.sqlite3")
    db.initialize()
    with pytest.raises(ValueError):
        db.create_numbered_project("x", profile=profile("x"))
    fresh = ProjectApplicationService(db).create_numbered_offline_project(profile())
    assert fresh.display_number == "SC-0001"
