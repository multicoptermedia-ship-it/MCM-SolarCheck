# Chunked SFTP staged delivery prototype

`ChunkedStagedUploadDelivery` accepts a binary readable stream and processes it in bounded chunks (default 1 MiB), calculating SHA-256 as chunks are written. It then reads remote staging in bounded chunks, verifies length and hash, and publishes only if both match. Staging cleanup is attempted on all exits. The SFTP backend is an **injected transport interface**; no real IONOS connection is made.

The transport must implement exclusive streaming staging writes, streaming reads, removal, and exclusive no-overwrite publication. Missing streaming capabilities fail closed. The adapter does not implement these operations with a concrete SFTP library, and ordinary SFTP rename must not be assumed to be exclusive or atomic.

**Resumption is not implemented yet.** Each attempt receives a new random staging key; an interrupted process can leave orphaned staging files. A future durable manifest should persist upload ID, authorized owner, expected size/hash, verified offsets, state transitions and expiration. Resumption must revalidate previously transferred bytes before appending and must never publish unverified data. Add cancellation, per-project quotas, bounded retry/backoff, storage sweeper and a safe publication protocol.

This prototype is not wired into the online HTTP route, job processing or production hosting. Remote benchmark and access-controlled staging tests require explicit approval. No credentials should be committed.
