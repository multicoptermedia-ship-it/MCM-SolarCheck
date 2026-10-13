# SSH/SFTP cleanup error precedence

The optional offline-only SFTP preflight now attempts to close all available resources when an inspection fails, while retaining the original handshake, host-key or directory-inspection exception. Without a primary failure, a cleanup exception remains visible to the caller.

This avoids misleading diagnosis when a socket or SFTP client also fails to close. Cleanup is best-effort: a failed close does not prove the underlying connection has been terminated. The code is not a production network lifecycle manager, does not implement retries or backoff, and does not guarantee remote read-only permissions.

The tests use fake clients and drivers. No IONOS network connection, credentials, remote writes, charges, deployment or merge into main.
