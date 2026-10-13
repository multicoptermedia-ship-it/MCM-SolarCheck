# Strict SFTP directory inspection – integrated

The optional Paramiko handshake driver now uses `open_strict_sftp_session`, which requires authenticated SSH and wraps the SFTP client in `StrictReadOnlySFTPSession`. Only a remote ENOENT means the configured directory is absent. Access-denied and recognized network errors propagate as typed errors rather than a misleading `False`.

Unit tests cover the strict factory with injected fake SFTP clients; no real IONOS connection has been made. This adapter is still opt-in and is not wired into production upload or publication.

Remaining limitations: Paramiko import is still lazy and its dependency availability has not been validated in deployment; unknown server error codes remain exceptions. Remote read-only access depends on server permissions, and exclusive publication/fencing is unverified. No secrets, network actions, costs or changes to `main`.
