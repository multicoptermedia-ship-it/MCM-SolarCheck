import sqlite3
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _profile():
    return ProjectProfile(customer_name="Solar GmbH",site_name="Anlage Nord",site_street="Solarweg 1",site_postal_code="47574",site_city="Goch",inspector="Pruefer",customer_contact="Kontakt",customer_email="kontakt@example.invalid",order_reference="AUF-42")


def test_project_profile_roundtrip(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P1","Projekt")
    db.save_project_profile("P1",_profile())
    assert db.project_profile("P1")==_profile()


def test_schema_v12_migrates_to_v13_with_profile_table(tmp_path):
    path=tmp_path/"legacy.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE schema_info(version INTEGER NOT NULL);
        INSERT INTO schema_info VALUES(12);
        CREATE TABLE projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO projects(project_id,name) VALUES('P1','Legacy');
        """)
    db=ProjectDatabase(path); db.initialize()
    with db.connect() as check:
        assert check.execute("SELECT version FROM schema_info").fetchone()[0]==13
        assert check.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_profiles'").fetchone() is not None
    db.save_project_profile("P1",_profile())
    assert db.project_profile("P1").site_name=="Anlage Nord"
