# Persistierte Auftragswarteschlange – nächster Integrationsschritt

Der SQLite-Jobstore kann mit `queued_jobs(limit=N)` offene Aufträge in FIFO-Reihenfolge lesen, auch nach erneutem Öffnen der Datenbank. `DurableQueuePump.tick()` übergibt diese Aufträge an den bestehenden `QueuedJobDispatcher`, der Kundenzugehörigkeit, atomare Kapazitätszulassung und Worker-Einplanung prüft. Die Standardkapazität bleibt zwei gleichzeitig laufende Aufträge.

**Noch nicht automatisch im Online-Server aktiviert:** `tick()` wird aktuell nur explizit aufgerufen. Es existiert noch kein laufender Hintergrund-Scheduler, kein verlässliches Wake-up nach Worker-Abschluss, keine Prozess-übergreifende Worker-Orchestrierung und keine sichere Behandlung von Jobs, die beim Absturz bereits `running` waren. Persistierte `queued`-Einträge können beim nächsten Aufruf wiedergefunden werden; das allein ist keine vollständige Crash-Recovery. Fehler nach der Zulassung und vor der Worker-Einplanung müssen ebenfalls gesondert abgefangen werden.

Die vorhandenen Kunden-, Worker-Claim-, Demo-, Zahlungs- und Berichtsgates bleiben unverändert. Keine Analyseergebnisse werden simuliert. Änderungen nur im Entwicklungsbranch, nicht auf `main`.
