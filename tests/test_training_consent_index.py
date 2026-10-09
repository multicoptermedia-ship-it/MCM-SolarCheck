"""SQLite consent lookup index exists for repeated project checks."""
import sqlite3
from mcm_solarcheck.infrastructure.sqlite_training_consent import SQLiteTrainingConsentStore


def test_latest_event_index(tmp_path):
    database = tmp_path / "consent.sqlite"
    SQLiteTrainingConsentStore(database)
    with sqlite3.connect(database) as connection:
        indexes = connection.execute("PRAGMA index_list(training_consent_events)").fetchall()
    assert "idx_training_consent_latest" in [item[1] for item in indexes]
