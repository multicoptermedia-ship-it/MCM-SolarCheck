# Conservative upload reconciliation (opt-in)

`UploadReconciliation(store).run_once(project_directory)` examines pending attempts with the stored size and SHA-256. Only verified, uniquely pending entries are finalized using a conditional SQLite update; rerunning skips completed entries. Missing, damaged, unsafe, legacy or competing pending entries stay pending and are returned with a `review_*` outcome. Files are never overwritten, retried, or deleted.

This is **not enabled automatically** in the HTTP server or deployment. The supplied directory resolver must enforce customer/project isolation. Hash verification and journal finalization are not an atomic filesystem operation: a concurrent file replacement can invalidate the check. A production-safe scheduler requires per-file coordination, secure filesystem reads, and real integration tests before automatic execution. A matching hash cannot independently establish which upload attempt wrote the file. No automatic deletion or customer notification is implemented.

## Additional conservative checks

The SQLite finalization guard also rejects any previous completed attempt for the same customer, project and filename. This avoids claiming an existing file for a newer attempt merely because its digest matches. Integrity inspection opens the file with `O_NOFOLLOW`, rejects hardlinks and non-regular files, and compares file descriptor metadata before and after hashing. Platforms without `O_NOFOLLOW` are classified as unsafe.

These checks do **not** provide a transaction across the filesystem and SQLite, do not lock out non-cooperating writers, and do not protect an untrusted directory resolver or parent-directory symlink replacement. Recovery remains opt-in and must not be scheduled automatically until those risks are addressed.
