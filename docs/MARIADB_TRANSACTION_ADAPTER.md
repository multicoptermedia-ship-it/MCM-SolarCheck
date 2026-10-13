# MariaDB-Adapter: opt-in Staging

`MariaDBJobLeaseAdapter` akzeptiert eine injizierte DB-API-Verbindungsfabrik und führt Claim, Renew und Complete mit parametrisierten SQL-Anweisungen in getrennten Transaktionen aus. Erfolg wird nur bei exakt einer geänderten Zeile gemeldet. Bei Fehlern wird ein Rollback versucht und die Verbindung geschlossen. Der Verbindungsaufbau erfolgt erst bei tatsächlicher Operation.

`build_mariadb_connection_factory` verlangt einen Passwortlieferanten und ein CA-Zertifikat. Der injizierte Treiber **muss** `ssl_context` und Hostnamenprüfung tatsächlich unterstützen; vor echter IONOS-Nutzung ist die konkrete Treiber-API und die IONOS-TLS-Konfiguration zu prüfen. Keine ungesicherte Fallback-Verbindung zulassen.

**Offene Punkte:** Die SQL-Tabellen sind bisher nur Entwürfe und noch nicht migriert. Der Adapter bietet noch keine serverseitige Zwei-Worker-Gesamtkapazität, keinen Queue-Pump, keine Recovery nach abgelaufenen Leases und keinen produktiven Datenbanktreiber. Der Online-/Offline-Speicherwechsel ist nicht verdrahtet. Kein Live-IONOS-Zugriff, keine Secrets, keine Kosten, kein Merge in `main`.
