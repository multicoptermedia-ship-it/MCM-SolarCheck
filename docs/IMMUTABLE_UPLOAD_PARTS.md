# Immutable upload parts — isolated prototype

Instead of appending to a shared staging file, an upload can be split into separately named, content-addressed parts: `.staging/parts/<transfer-id>/<six-digit-part-number>-<sha256>`. The writer validates each part, requires an exclusive-create operation from the injected backend, and reads back the stored bytes to verify their digest. Repeating an identical write is idempotent; a corrupt existing part is rejected.

This is **not yet a complete resumable upload implementation**. Parts are not durably listed in a manifest, reassembled, garbage-collected, or published. The current writer buffers one part in memory, bounded by the configured maximum. The remote interface is injected and tested with a fake; no IONOS connection or claim of atomic SFTP exclusive-create semantics is made.

For production: verify IONOS SFTP exclusive-create behavior under concurrent connections; add a durable part manifest with owner authorization, exact part order and size limits, immutable staging guarantees, crash recovery, atomic or fenced final publication, retention cleanup, cost and throughput measurements. Never treat a content digest alone as authorization to read another customer's data.
