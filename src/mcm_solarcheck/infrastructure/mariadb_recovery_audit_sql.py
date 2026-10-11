"""Proposed MariaDB recovery audit schema; never executed on import."""
from __future__ import annotations

RECOVERY_AUDIT_SCHEMA_SQL = """CREATE TABLE IF NOT EXISTS mcm_recovery_audit (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    job_id BIGINT UNSIGNED NOT NULL,
    slot_id TINYINT UNSIGNED NOT NULL,
    operator_id VARCHAR(200) NOT NULL,
    evidence_reference VARCHAR(200) NOT NULL,
    outcome VARCHAR(32) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT UTC_TIMESTAMP(6),
    INDEX ix_recovery_job (job_id, id),
    CONSTRAINT fk_recovery_job FOREIGN KEY (job_id) REFERENCES mcm_processing_jobs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""

INSERT_RECOVERY_AUDIT_SQL = """INSERT INTO mcm_recovery_audit
(job_id, slot_id, operator_id, evidence_reference, outcome)
VALUES (%s, %s, %s, %s, %s)"""
