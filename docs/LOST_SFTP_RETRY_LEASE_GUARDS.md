# Verlorene SFTP-Retry-Leases: Fail-closed-Checkpoints

Die neue `owns_live_lease`-Prüfung validiert Job-, Kunden-, Projekt-, Worker- und Token-Zuordnung sowie den Ablaufzeitpunkt und den weiterhin retryfähigen Zustand in einer SQLite-Transaktion. `SFTPPreflightRetryWorkGuard.require_live` bricht mit `LostRetryLeaseError` ab, wenn die Berechtigung fehlt. `GuardedSFTPPreflightRetryStep.run` prüft vor einem explizit übergebenen Arbeitsschritt und ruft ihn nur bei positiver Prüfung auf.

**Grenzen:** Diese Checkpoints sind optional und nicht in den produktiven Queue-Pump integriert. Zwischen Prüfung und Operation kann eine Lease ablaufen oder ersetzt werden (TOCTOU). Bereits laufende Schritte werden nicht unterbrochen. Weder SFTP-Remote-Fencing noch ein sicherer verteilter Abbruch wird behauptet; insbesondere dürfen irreversible Remote-Schreibvorgänge nicht allein auf diese Prüfung vertrauen. Es gibt keine automatische Wiederholung, keine echte IONOS-Verbindung und keinen Merge nach `main`.

Nächste Absicherung vor Produktivbetrieb: durchgehende Integration in den Worker-Lebenszyklus, Umgang mit Lease-Verlust und echte Remote-seitige Schreibabsicherung.
