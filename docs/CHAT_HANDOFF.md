# MCM-SolarCheck – Übergabe für einen neuen Chat

Stand: 18.10.2026. Verbindlicher Arbeitszweig: `feature/block38-offline-ai-ingestion-tests`.
Repository: https://github.com/multicoptermedia-ship-it/MCM-SolarCheck
Letzter bestätigter CI-Stand: Nutzer meldete „test grün“ nach gezieltem Hotfix `d4b068a2ac4ad904712c6792315b4574ee59fec0`. Der letzte reguläre Fünf-Commit-Block endete mit `ba46544a98784391584a85fe21f281b87cf6966b`.

## Produktziel und Architektur

Offline-first Windows-Anwendung für DJI Mavic 3T PV-Inspektion: Ein Flugordner mit bis zu 1.000 Auslösungen, je RGB und Thermal (bis zu 2.000 Dateien), wird ohne manuelle Einzelbildauswahl vollständig verarbeitet; per Bild/Batch sind Erfolg und Fehler sichtbar. Langfristiges Ziel: native hochauflösende, zoombare RGB-/Thermal-Orthofotos, menschliche Prüfung, freigegebener PDF-Bericht. Originale niemals herunterskalieren oder überschreiben; verkleinerte Arbeitsansichten klar als nichtmetrisch kennzeichnen. Thermische Farbpaletten-JPEGs sind keine kalibrierten Celsius-Temperaturen.

Eigenständige Implementierung, lediglich an Ideen von OpenDroneMap angelehnt: **keine ODM-/WebODM-Laufzeit, kein Docker-ODM, keine Kopie von ODM-Quellcode**. Lizenzen verwendeter Drittbibliotheken gesondert prüfen. Private DJI-Bilder, GPS und andere Kundendaten nicht committen. Nutzer wählen Ordner oder Dateien, nicht ZIP.

## Tatsächlich implementiert

- `services/flight_inventory.py`: DJI-Dateinamen zu RGB/Thermal-Auslösungspaaren gruppieren; fehlende Partner erkennbar.
- `services/flight_image_inspection.py`: alle erkannten Dateien auf Lesbarkeit, Dimensionen und Fehler prüfen, JSON-Export.
- `services/flight_batch_plan.py`: überlappende, begrenzte Capture-Gruppen planen, JSON; **Planung, noch kein geometrischer Batch-Merge**.
- `services/flight_rgb_link_run.py`: alle benachbarten RGB-Verbindungen mit bestehender ORB-/RANSAC-Registrierung prüfen; Status pro Link und optionaler Fortschrittscallback, JSON-Export. Die Arbeitsbilder werden begrenzt skaliert, Originale bleiben unverändert. Bei 1.000 Auslösungen sind 999 benachbarte Verbindungen vorgesehen; räumliche Überlappung ist nicht garantiert.
- `gui/import_page.py` und `gui/shell.py`: zusätzliche Ordneraktion „DJI-Flugordner: alle RGB-Bildverbindungen prüfen“, Fortschrittsdialog und lokale JSON-Ergebnisdatei. Der Lauf ist **noch synchron und nicht abbrechbar**; GUI kann während langer Verarbeitung eingeschränkt reagieren.
- Vorhandene 3–4-Bilder-Vorschau (`flight_visual_files.py`, `flight_native_rgb.py`, `visual_projective_preview.py`) ist nichtmetrisch und **keine vollständige Flugmosaik-Erzeugung**.
- Geprüfte Vermessungsdaten können über getrennte bestehende Pfade für GIS-/Orthofoto-Funktionen genutzt werden; das ist nicht gleichzusetzen mit einer automatischen Flugordner-Orthofoto-Pipeline.

## Noch nicht fertig

Echter asynchroner Worker mit Abbruch, vollständige per-Capture-/Batch-Fortschrittsdarstellung, robuste globale geometrische Registrierung, disk-basierte Kacheln, hochauflösender RGB-/Thermal-Mosaikexport aus vollständigen Flügen, belastbare metrische Orthofoto-Prüfung, radiometrische Temperaturkalibrierung und durchgehender Review-/PDF-Ablauf aus diesem neuen Flugordnerpfad.

## Nächster geplanter Block

Den vollständigen RGB-Linklauf in einen **Qt-Hintergrund-Worker** verlagern: bedienbare GUI, Thread-sichere Fortschrittsanzeige, verlässlicher Abbruch und nachvollziehbare Teil-/Fehlerstatus. Anschließend geometrische Zusammenführung und native Kachelausgabe vertikal vorantreiben. Keine irreführende Orthofoto-Fertigmeldung.

## Verbindlicher GitHub-Arbeitsrhythmus

- Nutzer meldet **„alle grün“ / „test grün“**: CI-Erfolg bestätigen, **keine Änderungen**, auf „bitte weiter“ warten.
- Nutzer sagt **„bitte weiter“** nach Grün: **genau fünf unterschiedliche Commits** auf dem Feature-Branch; fünfter aktualisiert `docs/DEVELOPMENT_AGREEMENT.md` mit Übergabe. Danach CI-Status erfragen.
- Nutzer sagt **„rot“ / „teilweise rot“**: aktuelle GitHub Actions samt Joblogs prüfen, **nur gezielter Hotfix**, kein neuer Fünferblock.
- **Kein Merge nach `main`** ohne ausdrückliche Freigabe.
- Diese Übergabedatei und `docs/DEVELOPMENT_AGREEMENT.md` zu Beginn eines neuen Chats lesen; GitHub-Branch/CI-Status verifizieren.

## Letzte Commits

Letzter regulärer Block: `254894e` (Fortschritt), `484e62d` (GUI-Ordneraktion), `08177d3` (GUI-Service-Verbindung), `4255aa3` (Tests), `ba46544` (Dokumentation).
Gezielter CI-Hotfix: `d4b068a` korrigiert den GUI-Test ohne verfügbare `qapp`-Fixture. Danach meldete der Nutzer grün.
