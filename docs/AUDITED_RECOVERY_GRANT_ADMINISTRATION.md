# Audited recovery grant administration

Use `AuthorizedGrantAdministration` with `SQLiteAuditedRecoveryGrants` for explicitly administered recovery permissions. The trusted caller must authenticate the administrator and construct `GrantAdministrator` with `publication:manage_grants`; recovery permission `publication:reconcile` alone is insufficient to change grants.

Grant updates and audit entries are written within one SQLite transaction using `BEGIN IMMEDIATE`. If audit insertion fails, the permission change is rolled back. Revocations are audited with the previous and next grant values. The `allowed` method is compatible with `ProjectAuthorizedRecoveryService`.

**Integration caution:** The older `SQLiteRecoveryGrants.set_grant` remains an unaudited mutation API. For full audit coverage, all trusted administrative write paths must be migrated to the audited implementation and legacy direct writers disabled. No public HTTP administration, authentication integration, or operator onboarding is implemented. SQLite audit history is append-only through the API, not tamper-proof against database administrators. Cross-host access and remote SFTP publication still require separate design and verification.
