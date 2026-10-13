# IONOS SFTP staged upload integration plan

The new `SFTPStagedUploadBackend` is a transport-injected **prototype**. It does not open SFTP connections, use customer credentials, provision hosting, or run in the HTTP upload service. Tests use an in-memory transport only.

## Required remote capabilities

- Private upload root, restricted SFTP account, dedicated `.staging` directory and explicit per-customer/project access controls.
- Exclusive creation of staging files, reliable readback for size/SHA-256 verification, and exclusive publication that **cannot overwrite** an existing final object. Ordinary SFTP rename is not assumed to provide this property. If the server cannot guarantee it, publication must fail closed or use a separately validated manifest/commit design.
- Interrupted-transfer cleanup, retry journal, visibility rules for readers, and audited recovery after worker crashes.
- Worker access and remote capacity/bandwidth benchmarks, timeouts, quotas, monitoring and cost limits.
- Validate server-side atomicity and durability experimentally on the actual IONOS webspace before enabling production.

The current service buffers the complete payload in memory. Large RGB/thermal datasets will need chunked streaming and bounded-memory hashing, resumable staging with integrity checks, and explicit cancellation. Never infer successful transfer from a socket close alone.

Do not store passwords or SFTP private keys in Git. Deployment and any billable remote tests require separate authorization. No external transfer or deployment has occurred.
