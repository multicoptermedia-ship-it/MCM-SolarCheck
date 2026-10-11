# Exklusive SFTP-Retry-Leases (opt-in)

`SQLiteSFTPPreflightRetryLeases` verwaltet eine separate Lease-Tabelle **in derselben SQLite-Datei** wie `SQLiteSFTPPreflightRetries`. Eine Claim-Transaktion mit `BEGIN IMMEDIATE` prüft Kunden-/Projektzuordnung, gespeicherte Wartezeit, Retry-Grenze und bestehende Lease, bevor ein zufälliges Token und ein Ablaufzeitpunkt gespeichert werden. Gleichzeitige Claims über dieselbe SQLite-Datei können deshalb nicht beide erfolgreich sein. Die Freigabe verlangt dieselbe Job-/Projekt-/Worker-Identität und das passende Token.

**Sicherheitsgrenzen:** Ein abgelaufener Lease darf neu beansprucht werden, aber das alte Token wird dadurch nicht zu einem echten Fencing-Mechanismus für externe SFTP-Schreibvorgänge. Die Leases autorisieren keine Remote-Operationen. Es gibt noch keine Lease-Verlängerung, keine atomare Kombination aus Claim und tatsächlicher Ausführung, keine automatischen Wiederholungen und keine produktive Worker-Anbindung. Das System setzt eine gemeinsam erreichbare SQLite-Datenbank und vertrauenswürdige, synchronisierte UTC-Zeit voraus. Die bisherige Anzahl registrierter Fehlschläge ist nicht identisch mit einer garantierten Anzahl gestarteter Versuche.

Tests verwenden lokale SQLite-Dateien und parallele Threads; es wurden keine IONOS-Verbindungen aufgebaut, keine Kosten ausgelöst und keine Änderungen an `main` vorgenommen.
