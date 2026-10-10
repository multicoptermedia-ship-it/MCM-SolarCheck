# Publication recovery planning and destination reservations

`PublicationRecoveryPlanner` reads an owner-scoped publication journal and a read-only final-file inspection. It never changes journal state, retries an upload, overwrites a file or deletes data. It separates a missing final file, a verified final file and an unsafe/unavailable final file into manual review decisions. A recorded `published` state is not considered fresh proof of integrity.

`SQLitePublicationDestinations` reserves one exact destination string per transfer and one transfer per destination. Reservations persist across process restarts and are idempotent only for the same identity. The store must use the **same shared database** across all local workers to enforce uniqueness; it is not automatically coupled to the publication journal and does not lock a remote SFTP namespace.

Before production, normalize and generate destination paths server-side, enforce customer authorization, couple reservation and journal writes transactionally, establish immutable final bytes, handle directory replacement/symlinks, add a durable recovery decision workflow with operator approval, and test the actual IONOS SFTP behavior. Neither module is wired to the customer upload HTTP route. No external storage or billable compute was accessed.
