# Isolierte SFTP-Vorprüfung und Retry-Empfehlungen

Der optionale `IsolatedQueuedSFTPPreflightBatch` prüft wartende Queue-Einträge nacheinander und fängt Fehler **pro Auftrag** ab. Ein SFTP-Fehler von Kunde A verhindert damit nicht, dass die Vorprüfung für Kunde B fortgesetzt wird. Die Ergebnisse enthalten nur Job-/Projektkennungen, Status und eine grobe Fehlerkategorie; ursprüngliche Ausnahmetexte werden nicht im Ergebnis gespeichert.

`advise_sftp_preflight_retry` gibt bei Netzwerk- und Timeout-Fehlern ausschließlich eine Empfehlung für höchstens drei Versuche mit Backoff. Authentifizierungs-, Host-Key-, Berechtigungs-, unbekannte Fehler und fehlende Verzeichnisse erfordern zunächst manuelle Prüfung. Es existieren **noch keine automatischen Wiederholungen**, kein Backoff-Timer, keine persistierten Versuchszähler und keine Anbindung an die Job-Freigabe.

Die ältere `QueuedSFTPPreflightBatch` bleibt unverändert; die neue isolierte Variante ist bewusst opt-in. Queue-Fehler vor dem einzelnen Aufruf, beispielsweise beim Lesen aus der Datenbank oder beim Erstellen ungültiger Job-Identitäten, werden weiterhin nach außen gemeldet. Kein realer IONOS-Zugriff, kein Deployment und kein Merge in main.
