# Server-derived reserved publication paths

`CanonicalReservedLocalPublication` no longer accepts a caller-selected final destination. It derives the path from a configured absolute storage root and validated customer/project/transfer identifiers, checks that the target customer/project directory already exists, and delegates to reservation-first local publication.

`PublicationReservationAudit` compares a journal entry with the durable destination reservation read-only. Its `consistent_metadata` result means only that the two metadata records agree; it does **not** verify file bytes or prove publication is complete.

**Important remaining limits:** directory components above the final project directory can still be symlinks; path checks are subject to time-of-check/time-of-use races. Harden using trusted directory descriptors, no-follow opens and an authorized provisioning workflow before production. Reservation and journal remain separate SQLite transactions, and local hard-link semantics do not transfer to IONOS SFTP. This code is not wired to online customer uploads and does not create directories, deploy, or use paid workers.
