# Durable local publication journal and recovery inspection

`SQLitePublicationJournal` stores a single owner-scoped publication record per transfer, including destination, canonical expected size/hash supplied by its caller, and states `prepared`, `publishing`, `published`, `needs_review`. Conditional SQLite transitions prevent two journal writers from claiming the same `prepared` state. It does not atomically commit a filesystem publication.

`LocalPublicationReconciler` inspects a previously recorded destination read-only after restart. It reports `missing_final`, `verified_final`, `invalid_final`, `changed_during_read`, `unavailable`, `already_recorded`, or `not_found`. It does **not** automatically retry, delete, publish, or mark a transfer complete. In particular, `already_recorded` only describes the journal state and is **not** a fresh file-integrity check.

Production integration must derive and validate the destination from trusted server-side transfer metadata, not user input; implement safe directory handles and ownership checks; lock/fence across hosts; reconcile file publication and durable state; ensure immutable final bytes; and handle ambiguous fsync failures. No live IONOS SFTP connection, customer HTTP route, or production recovery scheduler is included.
