# Upload journal integrity verification

New upload attempts persist the received byte count and SHA-256 digest before the filesystem store operation. Existing SQLite journals are migrated in place by adding nullable columns. Legacy records remain readable and are **not** assumed verified.

`UploadAttemptRecovery.inspect_integrity(project_directory)` reads pending records and classifies files as `verified`, `file_absent`, `file_present_unverified`, `size_mismatch`, `hash_mismatch`, or `unsafe`. It does not write, retry, finalize, or delete files. The project directory resolver must enforce customer isolation and safe paths. This is a point-in-time check, not an atomic proof against concurrent file replacement; production recovery still needs concurrency-safe reconciliation and integration tests.
