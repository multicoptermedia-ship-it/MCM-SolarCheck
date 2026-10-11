# Dauerhaftes SFTP-Retry-Ergebnisjournal (opt-in)

`SQLiteSFTPRetryOutcomeJournal` speichert ausschließlich die bereinigten Ergebnisse `ready` und `missing_directory`, zusammen mit Job-, Kunden-, Projekt- und Worker-Zuordnung sowie Zeitstempel. Das Lease-Token wird intern zur Wiederholungs- und Eigentumsprüfung gespeichert, aber von `history` nicht ausgegeben. Pro Job und Token ist höchstens ein unveränderlicher Ergebniseintrag möglich.

`record` prüft in einer SQLite-`BEGIN IMMEDIATE`-Transaktion die exakt zugehörige, noch aktive Reservierung und den wartenden Retry-Ledger-Eintrag. Veraltete Tokens führen zu `lease_lost`; erneute identische Einträge zu `already_recorded`, abweichende zu `conflict`. Der opt-in-Dienst `JournaledSFTPRetryPreflight` führt eine einzelne Vorprüfung durch und gibt die Reservierung auch bei Fehlern frei.

**Grenzen:** Das Journal ist kein globaler Remote-Fencing-Mechanismus. Es schützt nur SQLite-Ergebniseinträge im selben Datenbankbestand. Es gibt keine automatische Retry-Planung, keine produktive Queue-Integration, keine echte IONOS-SFTP-Verbindung und keine Kosten. Die Lesehistorie ist nach Identität gefiltert; Authentifizierung und Berechtigungsprüfung müssen von einem vertrauenswürdigen Aufrufer erfolgen. Der Datenbankzugang selbst bleibt privilegiert. Kein Merge nach `main`.
