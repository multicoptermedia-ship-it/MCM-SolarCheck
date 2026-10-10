# Fresh local publication verification and recovery

`DescriptorPublicationVerifier` opens the customer/project directory using no-follow POSIX descriptors and hashes the final file by opening its basename relative to the pinned directory. It checks size, SHA-256 and file metadata before/after reading, without changing publication state.

`CanonicalPublicationReconciler` validates that the owner-scoped journal destination matches the canonical server-generated path and **always** verifies file bytes, including when the journal says `published`. The canonical reserved workflow uses this reconciler by default; the legacy generic reconciler remains unchanged.

Possible observations include `verified_final`, `invalid_final`, `missing_final`, `changed_during_read`, `unavailable`, `invalid_destination`, and `not_found`. This is read-only detection, **not automatic crash recovery**. An ambiguous publication still needs operator review and carefully authorized journal transitions. The root's ancestors, source inode immutability, cross-process write races, and atomicity across filesystem/journal/reservations remain unresolved. No IONOS SFTP, HTTP, deployment or paid compute is activated.
