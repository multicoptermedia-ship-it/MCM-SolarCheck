# Queue → SFTP: isolierte Read-only-Vorprüfung

Der neue optionale `build_queued_sftp_preflight(store, connector, config)` verbindet die bestehenden gespeicherten Queue-Identitäten mit dem projektgebundenen SFTP-Session-Manager. `tick()` liest höchstens `batch_size` wartende Jobs, entfernt doppelte Job-IDs im Snapshot und prüft ausschließlich das jeweilige Kunden-/Projektverzeichnis. Die injizierte Connector-Schnittstelle muss die Host-Key-Prüfung und Sitzungsfreigabe bereitstellen. Die Voreinstellung begrenzt Sitzungen **pro Prozess** auf zwei.

**Keine automatische Job-Freigabe:** Diese Vorprüfung verändert keine Jobzustände, beansprucht keine Worker, startet keine dauerhafte Queue-Pumpe und überträgt keine Dateien. Die bestehende `DurableQueuePump` und der `QueuedJobDispatcher` bleiben unverändert. Ein Verzeichnischeck allein ist keine Autorisierung für einen Auftrag und kein Beleg für verfügbare Daten. Bei Fehlern bricht der Batch ab; er führt keine automatischen Wiederholungen aus.

Vor der produktiven Verknüpfung fehlen unter anderem eine verbindliche Authentisierung/Owner-Prüfung der Queue-Einträge, eine globale Kapazitätsgrenze über mehrere Prozesse, definierte Retry-/Timeout-Regeln, ein Schutz vor serverseitigen Symlinks und reale IONOS-Verifikation. Keine IONOS-Verbindung oder kostenpflichtige Aktion in diesem Block.
