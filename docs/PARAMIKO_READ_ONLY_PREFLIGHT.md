# Optional Paramiko SFTP preflight adapter

`build_paramiko_read_only_probe(credentials_provider=...)` is an **opt-in** adapter. No live network access occurs on import or construction. The connector calls `Transport.start_client` without authentication, checks the server public-key SHA-256 fingerprint against the configured pin, and only then requests password credentials and authenticates. A read-only SFTP `stat` check can then inspect the configured root.

Paramiko is an optional runtime dependency and is imported lazily. Unit tests use injected fake sockets and transports; no IONOS connection was made.

Security and operational limitations:
- SSH fingerprint must be independently verified; do not trust a fingerprint obtained from the same untrusted first connection.
- Credentials must come from an approved secrets provider; never commit or paste them in chat.
- The current driver supports only password authentication. Key-based login, host-key rotation, SSH algorithm policy and connection pooling are not yet implemented.
- `directory_exists` treats any remote `OSError` as absent, including permission and network failures; this needs stronger error classification before operational monitoring.
- Read-only is enforced by the narrow exposed session API, **not** by server-side SFTP permissions.
- The adapter is not wired to production upload, publication, workers, HTTP or IONOS deployment. Live staging checks require explicit authorization.
- No claim of remote exclusive publish, remote fencing, or safe concurrent SFTP rename is made.
