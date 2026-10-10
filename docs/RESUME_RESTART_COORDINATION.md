# Resume coordination and restart inspection

The opt-in `SQLiteResumeLocks` adapter reuses the existing SQLite upload lease implementation. Two cooperating processes sharing one database cannot hold the same transfer lease simultaneously while the lease remains valid. Different transfers may proceed independently.

`ResumeRestartRecovery.inspect` reopens durable manifest state, acquires the transfer lock, checks the complete original source and reads the staged remote prefix. It returns a status and offset **without appending, publishing, or changing the manifest**. The caller must provide the original source again; this component does not locate customer files after a restart.

**Not production-safe yet:** lease expiry or heartbeat loss is not a remote write fence; a stale worker may continue writing. SFTP does not necessarily support atomic conditional append. A production solution needs a transport-level fencing token or immutable upload parts, a durable source reference, robust recovery of publication crashes, and tested cross-host coordination. No actual IONOS SFTP connection is performed. These services are not wired to the HTTP upload route.
