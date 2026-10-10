# Ordered SSH handshake integration (offline-only)

The opt-in `build_ordered_verified_sftp_probe(driver_factory)` requires the injected driver to implement:

1. `negotiate_without_authentication()`: establish SSH transport and negotiate server key, **without sending credentials**.
2. `negotiated_host_key_blob()`: expose the negotiated raw SSH host public-key blob.
3. `authenticate()`: authenticate only after the SHA-256 fingerprint has been verified.
4. `open_read_only_sftp()`: return a read-only session supporting `directory_exists(path)` and `close()`.
5. `close()`: close the transport on any failure or normal exit.

The injected driver is a **trusted boundary**: its internal behavior cannot be proven by these unit tests. A real SSH-library adapter must disable automatic host-key acceptance, ensure negotiation is unauthenticated, and enforce read-only remote operations as far as the server permits. No concrete SSH-library driver is included in this batch. The current `SFTPStorageConfig` validates only the fingerprint's basic shape, not its canonical base64 digest format; actual matching is enforced by the fingerprint comparison.

No IONOS network connection, credentials, remote writes, live deployment or paid operations. Before staging integration, review the chosen SSH library and add controlled integration tests with explicit authorization.
