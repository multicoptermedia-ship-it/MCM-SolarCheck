# Remote immutable part verification (read-only prototype)

`RemoteImmutablePartVerifier` reads owner-scoped ordered part metadata, checks expected part count and total size, and streams each remote part in bounded chunks. It compares each part's actual byte count and SHA-256 with its durable manifest record. It returns `verified_parts` only after all parts pass. The read-only backend adapter validates canonical part paths before calling an injected transport.

This is **not** a full-file verification or safe publish operation. The expected count and total size must eventually come from an authorized canonical transfer record, not untrusted caller parameters. A full-file SHA-256 must be computed across all parts in order before publication, with immutable storage or a fenced commit to prevent changes after readback.

There is no real IONOS SFTP connection, no remote write, no final assembly, no automatic restart scheduler and no customer-facing activation. Transport failures and malformed chunks fail closed. Before production, test actual SFTP semantics and add owner authorization at the integration boundary, source-of-truth consistency, timeouts, cleanup and retry policy.
