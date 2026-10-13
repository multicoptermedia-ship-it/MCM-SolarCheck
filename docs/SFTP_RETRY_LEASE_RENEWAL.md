# SFTP-Retry-Leases verlängern und prüfen

Die opt-in-Schnittstelle `SFTPPreflightRetryClaimService.renew(..., token, now=None, lease_seconds=60)` verlängert ausschließlich eine **noch gültige** Reservierung mit passender Job-, Kunden-, Projekt- und Worker-Identität sowie korrektem Token. Eine Verlängerung verkürzt keine bestehende Ablaufzeit. SQLite `BEGIN IMMEDIATE` serialisiert die Prüfung und Änderung innerhalb derselben Datenbank.

`SFTPPreflightRetryLeaseInspector.inspect(...)` gibt read-only `not_leased`, `active`, `expired` oder `invalid_lease` zurück. Das Worker-Token wird nicht ausgegeben. Ein fremder Kunde erhält keinen Zugriff auf die Lease-Informationen.

**Grenzen:** Keine automatische Heartbeat-Schleife, keine Netzwerkaktionen, keine automatische Queue-Wiederholung, keine produktive IONOS-Verbindung. Die Gültigkeit hängt von vertrauenswürdiger UTC-Zeit ab. Token-gebundene SQLite-Leases sind **kein Remote-Fencing**: ein alter Worker kann externe SFTP-Operationen möglicherweise trotzdem ausführen. Eine tatsächliche Worker-Anbindung erfordert vor jedem Schritt zusätzliche Prüfungen, robuste Behandlung von Lease-Verlust und für gefährliche Schreiboperationen ein vom Remote-System unterstütztes Fencing-Verfahren. Keine Änderungen an `main`.
