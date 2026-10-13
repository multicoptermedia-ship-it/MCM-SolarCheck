"""MariaDB staging schema proposal, intentionally not executed automatically.

All tables use InnoDB and foreign keys; binary file payloads remain on SFTP.
"""
from __future__ import annotations

MARIADB_STAGING_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS mcm_projects (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        customer_id VARCHAR(100) NOT NULL,
        project_key VARCHAR(100) NOT NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        UNIQUE KEY uq_customer_project (customer_id, project_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS mcm_processing_jobs (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        project_id BIGINT UNSIGNED NOT NULL,
        job_key VARCHAR(100) NOT NULL,
        state VARCHAR(24) NOT NULL DEFAULT 'queued',
        worker_id VARCHAR(100) NULL,
        lease_token CHAR(32) NULL,
        lease_expires_at DATETIME(6) NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        UNIQUE KEY uq_job_key (job_key),
        KEY ix_jobs_state (state, id),
        CONSTRAINT fk_job_project FOREIGN KEY (project_id)
            REFERENCES mcm_projects(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS mcm_project_files (
        id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
        project_id BIGINT UNSIGNED NOT NULL,
        storage_key VARCHAR(512) NOT NULL,
        file_kind VARCHAR(32) NOT NULL,
        byte_size BIGINT UNSIGNED NOT NULL,
        sha256 CHAR(64) NOT NULL,
        created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
        UNIQUE KEY uq_project_storage (project_id, storage_key),
        CONSTRAINT fk_file_project FOREIGN KEY (project_id)
            REFERENCES mcm_projects(id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)
