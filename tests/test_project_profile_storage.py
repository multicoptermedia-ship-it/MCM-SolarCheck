import sqlite3
from mcm_solarcheck.domain.project_profile import ProjectProfile
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _profile():
    return ProjectProfile(customer_name="Solar GmbH",site_name="Anlage Nord",site_street="Solarweg 1",site_postal_code="47574",site_city="Goch",inspector="Pruefer",customer_contact="Kontakt",customer_email="kontakt@example.invalid",order_reference="AUF-42",site_timezone="Europe/Berlin")


def test_project_profile_roundtrip(tmp_path):
    db=ProjectDatabase(tmp_path/"p.sqlite"); db.initialize(); db.create_project("P1","Projekt")
    db.save_project_profile("P1",_profile())
    assert db.project_profile("P1")==_profile()


def test_schema_v12_migrates_through_v14_with_profile_table(tmp_path):
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
        assert check.execute("SELECT version FROM schema_info").fetchone()[0]==14
        assert check.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_profiles'").fetchone() is not None
        columns={row[1] for row in check.execute("PRAGMA table_info(project_profiles)")}
        assert "site_timezone" in columns
    db.save_project_profile("P1",_profile())
    assert db.project_profile("P1").site_name=="Anlage Nord"


def test_schema_v13_migrates_to_v14_with_nullable_site_timezone(tmp_path):
    path=tmp_path/"legacy-v13.sqlite"
    with sqlite3.connect(path) as db:
        db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE schema_info(version INTEGER NOT NULL);
        INSERT INTO schema_info VALUES(13);
        CREATE TABLE projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO projects(project_id,name) VALUES('P1','Legacy');
        CREATE TABLE project_profiles(
            project_id TEXT PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
            customer_name TEXT NOT NULL, site_name TEXT NOT NULL, site_street TEXT NOT NULL,
            site_postal_code TEXT NOT NULL, site_city TEXT NOT NULL, inspector TEXT NOT NULL,
            customer_contact TEXT, customer_street TEXT, customer_postal_code TEXT,
            customer_city TEXT, customer_email TEXT, customer_phone TEXT,
            customer_reference TEXT, order_reference TEXT
        );
        """)
    db=ProjectDatabase(path); db.initialize()
    with db.connect() as check:
        assert check.execute("SELECT version FROM schema_info").fetchone()[0]==14
        columns={row[1] for row in check.execute("PRAGMA table_info(project_profiles)")}
        assert "site_timezone" in columns
