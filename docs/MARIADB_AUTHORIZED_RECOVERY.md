# MariaDB: explizit autorisierte Recovery

`MariaDBAuthorizedRecovery` ist ein **nicht angebundener Opt-in-Prototyp**. Eine `QuiescenceProof` enthält Job-ID, Slot-ID, altes Lease-Token, Operator und Evidenzreferenz. Ein injizierter, vertrauenswürdiger Verifier muss vor der Transaktion **explizit `True`** liefern. Dieser Verifier existiert noch nicht als produktive Integration.

Danach sperrt eine InnoDB-Transaktion das exakt tokengebundene Job-/Slot-Paar, verlangt beidseitig abgelaufene Leases und aktualisiert Job sowie Slot atomar. Bei Fehler, Tokenwechsel oder Wiederholung: kein erfolgreicher Commit. Der Job geht zurück nach `queued`, aber **kein Worker wird automatisch gestartet**.

**Vor realem Einsatz zwingend:** Authentisierung/Autorisierung der Operatoren; unveränderliche, prüfbare und widerrufbare Quiescence-Nachweise; Verhinderung einer Wiederaufnahme des alten Workers; remote Fencing vor SFTP-Publikation; persistentes Audit; konsistente DB-Serverzeit (aktuell erfolgt die Vorprüfung mit App-Uhr, SQL mit Serveruhr); Isolation/Deadlock-Tests auf MariaDB 11.8; Migration-Runner und Queue-Integration. Der Verifier-Aufruf liegt derzeit außerhalb der DB-Transaktion, weshalb dessen Aussage nur dann sicher ist, wenn die Stilllegung dauerhaft und nicht rückgängig zu machen ist.

Keine Live-Verbindung zu IONOS, keine Zugangsdaten, kein Deployment und kein Merge nach `main`.
