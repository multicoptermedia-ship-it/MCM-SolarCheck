# Streaming immutable-part assembly verification

`ImmutablePartAssemblyVerifier` reads remote parts in part-number order, validates every part's stored size and SHA-256, and incrementally calculates the complete file SHA-256 without concatenating the file in RAM. A `verified_file` result means all checks passed during that read. It **does not** create, write, assemble on disk, publish, or activate the file.

`AuthorizedPartAssemblyInspection` obtains expected file size and SHA-256 from the owner-scoped durable transfer manifest rather than caller-provided values. The part count is still supplied by the caller and needs canonical derivation or verification before production.

The readback-to-publication race remains: remote data could change after inspection unless parts are truly immutable and final publication is fenced. Part metadata writes are not transactionally coupled to remote writes. No actual SFTP connection or customer HTTP integration exists. Production needs a durable authorized part count, immutable remote storage semantics, crash-safe streaming final assembly and exclusive publish, full post-publication verification, cleanup and recovery.
