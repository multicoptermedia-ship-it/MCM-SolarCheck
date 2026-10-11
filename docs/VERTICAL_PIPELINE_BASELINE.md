# Vertikale Pipeline: geprüfte Bestandsaufnahme (2026-10-11)

## Nachgewiesene Anknüpfungspunkte
- `importers/project.py:import_m3t_project`: DJI-M3T-RGB/Thermal-Import, Paarbildung, Fehlerstatistik.
- `services/project_processing.py:ProjectProcessingService`: Kunden-/Projektprüfung, Zustände, Heartbeat, Importpersistenz. **Keine vollständige Befund- und Reportpipeline.**
- `services/parallel_processing_workers.py`: maximal zwei laufende lokale Importaufträge, kein vollständiger verteilter Produktionsworker.
- `online/http_entrypoint.py` und `infrastructure/verification_http_server.py`: Online-Projekt-/Upload-/Job-Endpunkte; Runtime meldet `features_ready: false`.
- `README.md`: beschreibt testgestützte Review-/Report-Komponenten, weist Produktionsmodell, Normprüfung und Release ausdrücklich als offen aus.

## Harte Integrationsgrenzen
1. Kein behaupteter Defekt, wenn nur Import-/Pairingdaten vorliegen.
2. Ein Review muss explizit freigeben, bevor ein Bericht veröffentlicht wird.
3. Offline nutzt lokale Dateien/SQLite, Online MariaDB/SFTP; fachliche Pipeline bleibt dieselbe.
4. Externe IONOS-, GPU-, Zahlungs- und Produktionsintegration sind hier nicht geprüft.
5. Nachweis der End-to-End-Funktionalität benötigt einen echten, freigegebenen PV-Testdatensatz.

## Vertikales Inkrement 1
Ein isolierter, injizierbarer Ablaufvertrag für Import -> Analyse -> Review -> Report mit Fail-Closed-Gates und reproduzierbaren Unit-/Integrationstests. Keine automatische Aktivierung in der Online-Produktion.
