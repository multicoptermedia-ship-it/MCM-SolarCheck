# Request-scoped audited recovery composition

The opt-in composition is:

1. `SQLiteRecoveryAttempts` records a unique request claim.
2. `RequestScopedRecoveryCoordinator` executes **only** a newly claimed request.
3. `RequestAuditedRecovery` records a request-scoped `requested` event before calling `ExplicitPublicationReconciliation`, then records its outcome.
4. `RequestRecoveryInspector` can read the request-specific audit history and current state without mutating anything.

A previously completed request returns its persisted outcome without re-execution. An existing pending request is never automatically retried, even if the journal is now published. Failed audit writes propagate; a post-execution audit failure may leave the request pending despite a successful journal CAS. Inspect and review explicitly.

The caller **must** supply an authenticated, authorized operator identity; the services do not implement authorization or HTTP exposure. The composition is not automatically wired into the app, and existing legacy audit wrappers remain available. Audit events, attempt completion and publication journal transitions are separate SQLite transactions, not an atomic commit. The storage source is not proven immutable and this does not implement distributed fencing, real SFTP, or production deployment.
