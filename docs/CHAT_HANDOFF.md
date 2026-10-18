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

## Aktualisierte Übergabe – Qt-RGB-Segmentexport (18. Oktober 2026)

- Maßgeblicher Entwicklungsbranch: `feature/rgb-all-segments-export`; vorheriger grüner Stand `5594f218`.
- Fünf bereits vorgefundene Commits: `2b1195c` (abbrechbarer Qt-Worker), `1adbebc` (Importseitenaktion), `b9c8753` (asynchrone Shell-Anbindung), `43dd989` (GUI-/Worker-Tests), `b6fa69e` (Entwicklungsvereinbarung). Keine weiteren gleichartigen Features implementieren.
- CI auf `b6fa69e` rot: Tests nutzten die nicht installierte `qtbot`-Fixture. Gezielter Korrekturcommit `f3e5656` ersetzt sie durch eine native `QApplication`-Fixture; CI Python 3.11 und 3.12 für den Korrekturstand noch zu bestätigen.
- Bestehender Segmentexport bleibt lokal, auf acht Arbeitsbilder pro Segment begrenzt, mit PNG/JSON und Abbruch-/Fehlerstatus; kein metrisch verifiziertes Orthofoto und keine Kundenberichtfreigabe.
- Vor jedem neuen Fünferblock den aktuellen Remote-HEAD, neue Commits und CI prüfen und doppelte Implementierungen vermeiden. Im fünften Commit **beide** Dokumente `docs/DEVELOPMENT_AGREEMENT.md` und `docs/CHAT_HANDOFF.md` auf denselben Stand bringen.
- Für komplexe Entwicklungsarbeit ist GPT-6 mit Denkstufe „Sehr hoch“ bevorzugt, sofern nutzerseitig verfügbar; die Modelleinstellung kann der Agent nicht selbst ändern.
- Bei roten Tests gezielt korrigieren, nicht einen neuen Fünferblock beginnen. Nach bestätigtem Grün auf „bitte weiter“ warten. Kein Merge nach `main` ohne ausdrückliche Freigabe.

## Übergabe 18. Oktober 2026 – Begrenzte Vorschauen langer RGB-Segmente

- Branch `feature/rgb-all-segments-export`, Basis `a0deedb` (CI zuvor erfolgreich). Fünf Commits: `2ab79a3` (Sampling), `89a148f` (Samplingtests), `1d3663a` (Flugexport), `350a3a6` (Regressionstests), dieser Dokumentationscommit.
- Segmente mit mehr als acht Bildern erhalten beim vollständigen Flugexport eine **unvollständige, nichtmetrische** Vorschau aus maximal acht geordneten Arbeitsbildern. Kein vollständiges Flugorthofoto. Einzel-Segment-Export bleibt ohne explizites Sampling strikt.
- Qualitäts-JSON und Zusammenfassung kennzeichnen `source_frame_count`, `preview_frame_count`, `preview_incomplete`; `sampled_previews` zählt unvollständige Vorschauen. Originaldaten und Speichergrenzen bleiben geschützt.
- **CI Python 3.11/3.12 dieses Blocks noch prüfen**. Kein Merge nach `main`. Danach Nutzerbestätigung abwarten.
- Offen: unvollständige Vorschauen auch im Qt-Ergebnistext deutlich kennzeichnen; verifizierte GIS-Georeferenzierung und native kachelbasierte Vollauflösungsverarbeitung.
- Vor jedem neuen Fünferblock Remote-HEAD, CI und vorhandene Implementierungen prüfen; doppelte Arbeit vermeiden. Fünfter Commit aktualisiert beide Übergabedokumente gemeinsam. GPT-6 mit „Sehr hoch“ bevorzugt, soweit nutzerseitig verfügbar.

## Übergabe 18. Oktober 2026 – Qt-Kennzeichnung unvollständiger RGB-Vorschauen

- Vorheriger grüner HEAD `670ca2d` (Python 3.11 und 3.12 erfolgreich). Fünf Commits dieses Blocks: `5323c85` (Statusformatierung), `a89eba1` (Qt-Integration), `1c3777f` (Regressionstests), `88753ba` (verarbeitete Segmente anzeigen), dieser gemeinsame Dokumentationscommit.
- Qt zeigt nach dem Flug-Segmentexport die Zahl vollständiger und **unvollständiger** Segmentvorschauen, fehlgeschlagene/verarbeitete Segmente und Abbruch an. „Vollständig“ bedeutet hier nur, dass sämtliche Bilder eines **einzelnen Vorschau-Segments** berücksichtigt wurden, **nicht** ein metrisch oder GIS-geprüftes Flugorthofoto.
- Bestehende Offline-/Datenschutz-/Originalschutzgrenzen bleiben unverändert. Kein Merge nach `main`. CI für diesen neuen Block ist noch offen; Python 3.11/3.12 abwarten.
- **Verbindliche neue Abschlusskommunikation:** Nach jedem Fünferblock dem Nutzer mitteilen: umgesetzte Commits, tatsächliche Funktionen und Grenzen, offene Risiken, konkreten Vorschlag für den **nächsten** Fünferblock samt Nutzen sowie anstehende Richtungsentscheidungen und CI-Status. Vor der nächsten Umsetzung Gelegenheit zur Korrektur der Entwicklungsrichtung geben.
- **Vorschlag nächster Block:** Sicherheits- und Konsistenzhärtung der segmentweisen Qualitäts-/Summary-Ausgaben (atomare Dateiablage, Abbruch-/Teilresultate, klare Zuordnung der Vorschaubilder) und Tests. Alternativ nach Nutzerentscheidung zunächst Architektur/Prototyp für speichereffiziente native RGB-Kachelverarbeitung; niemals ungeprüfte Orthofoto-/GeoTIFF-Qualität behaupten.
- Vor jedem neuen Fünferblock Remote-HEAD, CI und vorhandene Funktionen prüfen, Duplikate vermeiden. Fünfter Commit aktualisiert **beide** Übergabedokumente. GPT-6 „Sehr hoch“ ist nutzerseitig bevorzugt, nicht durch den Agenten einstellbar.

## Übergabe 18. Oktober 2026 – RGB-Ausgabedateien sicherer bereitstellen

- Ausgangspunkt: `f9c00ff`, Python 3.11/3.12 grün. Genau fünf Commits: `9fc9018` (PNG-/JSON-Staging), `efe610c` (einmalige vollständige Qualitäts-JSON), `ae28677` (Regressionstests), `4fe2375` (Summary-Staging), dieser gemeinsame Dokumentationscommit.
- Segment-PNG und Qualitäts-JSON werden zuerst vollständig in temporäre Dateien im Zielordner geschrieben, anschließend mit exklusiver Neuerstellung veröffentlicht. Nach Fehlern werden Staging-Dateien bereinigt; bei Qualitäts-Publikationsfehler wird das neue PNG entfernt. Qualitätsmetadaten werden nun **einmal vollständig** geschrieben, nicht nachträglich überschrieben. Auch die Flug-Summary wird vor Veröffentlichung vorbereitet.
- **Wichtige Grenze:** Diese Veröffentlichung ist noch **keine transaktionale oder atomare Mehrdatei-Operation**. Stromausfall/Prozessabsturz während der Veröffentlichung kann Teilresultate hinterlassen; beim nächsten Block sind Crash-/Teildatei- und Race-Tests sowie atomare Einzeldatei-Publikation zu prüfen. Originale bleiben unverändert; keine metrisch verifizierte Orthofoto-Freigabe.
- CI Python 3.11/3.12 für diesen Block **noch offen**; kein Merge nach `main`. Nutzer nach Ergebnis fragen.
- **Nächster Fünferblock – Vorschlag:** Crash- und Konsistenzhärtung der Segment-/Summary-Publikation einschließlich Recovery- und Abbruchtests. Alternativ, nach Nutzerentscheidung, zunächst einen getrennten Architekturblock für speichereffiziente native RGB-Kachelverarbeitung priorisieren.
- Nach jedem Fünferblock: Commits, erreichte Funktionen/Grenzen, Risiken, nächster konkreter Vorschlag, Richtungsentscheidungen und CI-Status mitteilen; vor weiterer Umsetzung Nutzerkorrekturen ermöglichen. Vor jedem Block Remote-HEAD, CI und bestehende Funktionen prüfen; im fünften Commit **beide** Dokumente synchronisieren. GPT-6 „Sehr hoch“ ist nur nutzerseitig auswählbar.

## Übergabe 18. Oktober 2026 – Atomare Veröffentlichung einzelner RGB-Ergebnisdateien

- Basis `69f86e3` (Python 3.11/3.12 grün). Fünf Commits: `615aa2a` (PNG-/Qualitätsdateien als vollständige Hardlinks), `0744c47` (Summary-Hardlink), `ff0999d` (Fehler-Injektion angepasst), `c738c93` (Summary-/Kundendatenschutztests), dieser gemeinsame Dokumentationscommit.
- Staging-Dateien werden im Zielverzeichnis fertig geschrieben. Veröffentlichung per `os.link(..., follow_symlinks=False)` erstellt den **einzelnen** Zieldateinamen atomar und ohne Überschreiben existierender Ziele, statt inkrementell in sichtbare Zieldateien zu schreiben. Bei Fehlern werden temporäre Dateien entfernt, soweit der Prozess weiterläuft. Kein Überschreiben von Originalen/Kundendaten.
- **Grenzen:** PNG und Qualitäts-JSON sind zusammen weiterhin **keine atomare Transaktion**. Crash zwischen den beiden Veröffentlichungen kann ein einzelnes vollständiges PNG ohne JSON hinterlassen. Verwaiste temporäre Dateien nach Crash und fsync/Dauerhaftigkeit nach Stromausfall sind nicht abschließend behandelt. Hardlink-Unterstützung des Ziel-Dateisystems ist erforderlich; Fehlermeldungen statt stillschweigender unsicherer Fallbacks.
- CI Python 3.11/3.12 dieses Blocks noch nicht bestätigt; bei Rot gezielt korrigieren. Kein Merge nach `main`.
- **Nächster Block – Vorschlag:** Crash-Recovery-Strategie für verwaiste vollständige PNG/JSON-Paare und temporäre Dateien mit sicheren, expliziten Prüf-/Bereinigungsoptionen; oder nach Nutzerentscheidung Architekturprototyp für speichereffiziente RGB-Kachelverarbeitung. Keine ungeprüften metrischen Orthofoto-Aussagen.
- Nach jedem Fünferblock Commits, tatsächliche Fähigkeiten/Grenzen, Risiken, nächsten konkreten Blockvorschlag, Richtungsentscheidungen und CI nennen; auf Nutzerkorrekturen warten. Vor neuen Blöcken Remote-HEAD, CI und bestehende Implementierungen prüfen; im fünften Commit beide Übergabedokumente synchron aktualisieren. GPT-6 „Sehr hoch“ ist nutzerseitige Einstellung.

## Übergabe 18. Oktober 2026 – Sichere Diagnose unterbrochener RGB-Exporte

- Basis `bdfa2f2` (CI Python 3.11/3.12 grün). Fünf Commits: `334115b` (read-only Exportinspektion), `21672ac` (Sicherheitstests), `525cc4f` (Problemzähler/Prüfbedarf), `589b65a` (gültige Paare/Regressionstests), dieser gemeinsame Dokumentationscommit.
- `inspect_rgb_export_directory(output_dir)` erkennt isolierte Segment-PNG/JSON, ungültige Qualitätsmetadaten, verbliebene `.rgb-preview-*.tmp`/`.rgb-summary-*.tmp` und den Zustand der Flug-Summary. Es gibt Problemzähler und `requires_manual_review` zurück, **löscht oder verändert nichts**. Symlinks im Ausgabeverzeichnis werden konservativ abgewiesen.
- **Grenzen:** Dies ist nur eine Diagnose, **keine** automatische Wiederherstellung/Bereinigung, keine Byte-Validierung des PNG und keine vollständige Querprüfung der Summary gegen alle Segmente. Auch gültige Paare sind nicht metrisch verifizierte Orthofotos. Keine Änderungen an Originalen, Kundenberichten oder Freigaben.
- CI Python 3.11/3.12 für diesen neuen Block noch prüfen; bei Rot gezielt korrigieren. Kein Merge nach `main`.
- **Nächster Fünferblock – Vorschlag:** Prüfung der Dateiintegrität und der Zuordnung zwischen Summary und Segmentpaaren mit klaren, nichtdestruktiven Befunden; danach Architekturprototyp speichereffizienter RGB-Kachelverarbeitung. Nutzer kann die Reihenfolge ändern.
- Nach jedem Fünferblock Commits, Fähigkeiten/Grenzen, Risiken, nächsten konkreten Vorschlag, Entscheidungen und CI nennen; vor Fortsetzung Nutzerkorrekturen ermöglichen. Vor jedem Block Remote-HEAD, CI, offene PRs und vorhandene Implementierungen prüfen; fünfter Commit synchronisiert beide Dokumente. GPT-6 „Sehr hoch“ ist nutzerseitig auswählbar.
