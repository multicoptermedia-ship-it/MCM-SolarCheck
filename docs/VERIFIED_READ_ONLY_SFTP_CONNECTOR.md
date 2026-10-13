# Host-key-pinned read-only SFTP connector

`build_verified_sftp_probe(client_factory)` composes a read-only probe with a connector that compares the negotiated SSH public-key blob to the configured SHA-256 host-key fingerprint before exposing a session.

The client factory is injected and is **not** implemented here. A production integration must:
- Use a supported SSH/SFTP library with strict server host-key verification during SSH negotiation; never accept unknown keys automatically.
- Ensure no authentication credentials are sent to an unverified server. The current connector checks the key before calling `open_read_only_sftp`, but cannot guarantee that the injected factory did not authenticate earlier.
- Independently obtain and verify the expected host-key fingerprint out of band.
- Supply a read-only session whose `directory_exists` operation cannot mutate remote data.
- Handle timeouts, transport failures, cleanup, permissions and connection lifecycle.

The included fake-client tests prove local call ordering and mismatch rejection, **not** real SSH handshake safety or compatibility with IONOS. No actual network client, credentials, live connection, file transfer or publication is included. Explicit authorization is required before live testing.
