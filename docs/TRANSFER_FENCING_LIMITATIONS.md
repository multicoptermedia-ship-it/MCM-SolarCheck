# Transfer fencing: design and limits

`SQLiteTransferFences` allocates a durable, monotonically increasing generation for each transfer. A restarted or replacement worker can acquire a newer generation, invalidating earlier generations **in metadata**. Concurrent generation allocation is serialized using SQLite `BEGIN IMMEDIATE`.

`FencedStagedAppender` requires an injected remote operation named `append_chunks_if_generation_and_size(staging_key, generation, expected_offset, chunks)`. The backend must check **both** generation and offset atomically with the write. If the capability is absent, the adapter fails closed. Unit tests use an in-memory fake backend.

**Critical limitation:** SQLite generations by themselves do not stop an old worker from writing to a separate SFTP server. A check before an SFTP append has a time-of-check/time-of-use race. Ordinary SFTP has no portable atomic compare-generation-and-append operation. Therefore no IONOS SFTP backend is claimed to support this interface, and the new appender is deliberately **not** wired into the current resume coordinator or customer upload path.

Before production, choose and test a real fenced storage protocol (e.g. immutable upload parts with server-side exclusive publish), coordinate ownership and generation issuance, define recovery after partially completed writes, and test expiry, crash, contention, cross-host operation and storage semantics. The code is a safe-to-test foundation, not a completed cross-host fencing guarantee.
