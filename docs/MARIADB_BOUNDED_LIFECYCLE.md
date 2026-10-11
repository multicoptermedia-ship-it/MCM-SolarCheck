# MariaDB: atomare Verlängerung und Freigabe

`MariaDBBoundedJobLifecycle` erneuert oder beendet eine Reservierung nur, wenn Slot und Job gemeinsam einem Worker und demselben Lease-Token gehören und beide noch gültig sind. Eine Transaktion sperrt das Paar, prüft die Identität und aktualisiert beide Datensätze. Bei Null-Zeilen-Updates, verlorener Berechtigung oder Fehlern erfolgt Rollback.

Die neue optionale Komposition `build_mariadb_bounded_workers` stellt Admission und Lifecycle mit derselben Verbindungsfabrik bereit, ohne eine Verbindung aufzubauen. Der bisherige unbeschränkte `MariaDBJobLeaseAdapter` ist **nicht** als produktiver Claim-Weg geeignet.

**Wichtige Einschränkungen:** Der tatsächliche MariaDB-Treiber muss Transaktionen und `SELECT ... FOR UPDATE` bei deaktiviertem Autocommit garantieren. Der Slot-Lock allein schützt keine bereits gestartete externe GPU-Berechnung; externe Effekte brauchen eigene Fencing-/Idempotenz-Regeln. Recovery abgelaufener Leases, atomare Queue-Integration, Migration-Runner und Live-IONOS-Tests sind weiterhin offen. Keine Credentials, keine Migration auf IONOS, kein Merge nach `main`.
