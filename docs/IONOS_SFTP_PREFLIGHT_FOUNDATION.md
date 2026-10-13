# IONOS SFTP preflight foundation

This batch defines offline-only configuration validation, conservative remote capability policy, and an injected read-only inspection interface. No IONOS connection was made.

Before any authorized staging test:
- Obtain host, username, private remote root and an independently verified server host-key fingerprint through approved secret/config channels; never paste credentials into chat or commit them.
- Implement a connector that actually verifies the pinned host key and opens a read-only session. The current probe trusts that injected connector; it does not perform SSH verification itself.
- Confirm remote directory isolation, quotas, maximum file sizes, timeouts, reconnect behavior and server-supported SFTP operations.
- Test exclusive-create and final publication semantics under races and reconnects before setting any capability flags. Method names alone are not proof.
- Treat final publication as **unsupported** until remote exclusivity and fencing are independently demonstrated. Ordinary SFTP rename must not be assumed safe.
- Get explicit approval before any live upload, deletion, paid worker run or deployment.

The policy is an isolated planning component, not yet wired into upload execution. This is not a production SFTP client, and no automatic network activity is enabled.
