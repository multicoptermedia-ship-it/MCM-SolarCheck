# Reserved local publication

`ReservedLocalPublication` checks transfer ownership and pending state, reserves the absolute final path in `SQLitePublicationDestinations`, then delegates to the existing journalled exclusive local publisher. Different transfers cannot reserve the same destination when they share the same SQLite reservation database. A replay of the same transfer and destination is idempotent at the reservation layer.

`canonical_local_destination` supplies a deterministic server-owned path convention from validated customer, project and transfer tokens. It is **not yet wired** into `ReservedLocalPublication`; production callers must not accept arbitrary user-supplied destinations. Its root path and intermediate directories must be trusted and provisioned safely.

Important limits: reservation and journal transitions remain **separate transactions**, even if both stores point to the same SQLite file; crash recovery must reconcile them. No shared database across remote hosts is assumed. The local hard-link publisher is not an IONOS SFTP publisher, and remote atomicity, write fencing, final-file immutability and post-publication readback remain unverified. This module does not change the two-worker scheduling limit or wire customer uploads to the publication pipeline.
