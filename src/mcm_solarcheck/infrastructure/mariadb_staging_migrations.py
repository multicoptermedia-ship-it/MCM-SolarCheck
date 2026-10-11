"""Versioned, offline-only MariaDB staging migration plan.

Statements are never executed by importing this module.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.infrastructure.mariadb_staging_schema import MARIADB_STAGING_SCHEMA


@dataclass(frozen=True)
class MariaDBMigration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS = (
    MariaDBMigration(1, "initial_projects_jobs_files", MARIADB_STAGING_SCHEMA),
    MariaDBMigration(2, "bounded_processing_slots", (
        """CREATE TABLE IF NOT EXISTS mcm_processing_slots (
            slot_id TINYINT UNSIGNED NOT NULL PRIMARY KEY,
            job_id BIGINT UNSIGNED NULL,
            lease_token CHAR(32) NULL,
            expires_at DATETIME(6) NULL,
            CONSTRAINT fk_slot_job FOREIGN KEY (job_id)
                REFERENCES mcm_processing_jobs(id),
            UNIQUE KEY uq_slot_job (job_id),
            CONSTRAINT chk_slot_id CHECK (slot_id IN (1,2))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
        """INSERT IGNORE INTO mcm_processing_slots (slot_id) VALUES (1),(2)""",
    )),
)

MIGRATION_TABLE_SQL = """CREATE TABLE IF NOT EXISTS mcm_schema_migrations (
    version INT NOT NULL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    applied_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""


def pending_migrations(applied_versions):
    applied = set(applied_versions)
    if any(type(v) is not int or v <= 0 for v in applied):
        raise ValueError("invalid migration version")
    known = {migration.version for migration in MIGRATIONS}
    if applied - known:
        raise ValueError("unknown applied migration version")
    if applied != set(range(1, len(applied) + 1)):
        raise ValueError("migration history must be contiguous")
    return tuple(m for m in MIGRATIONS if m.version not in applied)
