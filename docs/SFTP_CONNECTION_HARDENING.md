# SFTP connection hardening – offline batch

This batch adds typed preflight errors, a conservative failure classifier, validated handshake timeouts (greater than zero and at most 120 seconds), and repeat-safe socket/transport cleanup. The timeout covers socket connection and SSH handshake arguments, **not** a proven end-to-end deadline for DNS, authentication, SFTP operations or all Paramiko internals.

The classifier intentionally returns `unknown` for ambiguous errors. It does not inspect or echo exception messages, which may contain secrets. Authentication and permission errors from the actual Paramiko library still require explicit safe translation at the adapter boundary; no reliable full error taxonomy is claimed.

Tests use injected fake transports and sockets. No IONOS staging connection, upload, credentials, deployment, worker charges or production wiring. Remote SFTP publication/fencing remains unverified and disabled by default.
