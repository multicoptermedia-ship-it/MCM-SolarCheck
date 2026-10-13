# MariaDB 11.8: IONOS-Staging-Grundlage

Die vom Nutzer bereitgestellte IONOS-Staging-Datenbank verwendet MariaDB 11.8 mit einem eigenen 2-GB-Kontingent. Der von IONOS vergebene Datenbankname wird als Konfigurationswert behandelt; es wird kein fester Name vorausgesetzt.

Die erste **nicht ausgeführte** SQL-Skizze umfasst Projekte, Verarbeitungsaufträge und Referenzen auf SFTP-Dateien. Große RGB-/Thermal-Dateien und Berichte verbleiben außerhalb der Datenbank. Die SQL-Vorlagen für Job-Reservierungen nutzen bedingte UPDATEs, Lease-Token, Datenbankzeit und müssen mit `rowcount == 1` sowie einer echten Transaktion verwendet werden. Das ist noch keine vollständige Multi-Worker-Implementierung und begrenzt nicht selbstständig zwei gleichzeitige Jobs.

**Sicherheit und Betrieb:** Zugangsdaten gehören ausschließlich in geschützte Laufzeitkonfiguration; keine Secrets in Git oder Chat. TLS-Zertifikatsprüfung und Erreichbarkeit vom späteren Worker sind vor einem echten Verbindungsaufbau zu klären. Die Datenbankstruktur ist ein Entwurf ohne Migration oder produktive Anwendung. Die bestehenden SQLite-Adapter bleiben für Offline-Betrieb und bisherige Tests bestehen. Noch keine Verbindung zu IONOS, keine Schemaänderung dort, keine kostenpflichtigen Worker und kein Merge nach `main`.
