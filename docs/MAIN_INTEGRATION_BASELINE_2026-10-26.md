# Integrationsbasis auf main – 26.10.2026

## Zweck und Freigabeumfang

Benutzerentscheidung vom 26.10.2026: Nach der systematischen Bestandsaufnahme aller 14 Branches werden die **bestehenden, erfolgreich getesteten** Entwicklungen in einem neuen, nachvollziehbaren **gemeinsamen Quellcode-Stand auf `main`** konsolidiert. Der Entwicklungszweig `feature/offline-human-report-approval` ist die **fachlich überprüfte Quelle**, nicht das frühere Minimal-`main`.

**Statusbegriff: INTEGRATIONSSTAND, KEIN PRODUKTIONSRELEASE.** Ein erfolgreicher Git-/CI-Stand belegt *nicht* lauffähige Gesamtphotogrammetrie, Windows-10-Hardwareabnahme oder ein metrisches PV-Orthofoto. Kein Installer, Downloadpaket, Datenmigrationslauf oder Kundendatenänderung wird durch die Branchübernahme ausgelöst.

## Technische Übernahmestrategie

1. Git-Vorgate geprüft: vormals `main` = `e523a30dff0cb6a17fc8d287289cadb9cbde28d8`, `feature/offline-human-report-approval` = `a32fbe26ffd609e09a2a79973b934ac893e33cec`, `compare(main...feature)` = `ahead` (4018 Commits) und **0 behind**. Damit ist ein konfliktfreier **Fast-forward** zulässig; `force=false` und erwarteten bisherigen `main`-HEAD als Sicherungsprüfung verwenden.
2. Voriger Source-HEAD `a32fbe26ffd609e09a2a79973b934ac893e33cec`: GitHub `tests` [grün](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40362304927) und `windows-offline-validation` [grün](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40362304745), Python 3.11/3.12.
3. Dieser Dokumentations-/Integrationsplan wird zunächst **auf dem aktiven Featurezweig** committed und muss dort erneut die gesamten CI-Gates bestehen. **Erst danach** darf `main` mit einer nicht erzwungenen Ref-Aktualisierung auf genau denselben Integrationscommit vorgesetzt werden.
4. Nach Fast-forward: `main` und der Featurezweig besitzen dieselbe exakte Commit-SHA und identischen Inhalt. `main` ist dann die maßgebliche Quellcode-Basis **für die nächste Arbeit**. Alte Release-/Experiment-/PR-Zweige bleiben erhalten; keine automatische Umstellung vorhandener PRs #3/#4.
5. Nach dem Ref-Wechsel: `main`-Commit verifizieren, CI-Läufe des exakten Commit-SHA dokumentieren, ausschließlich die neuen Quellcode-/Dokumentations-Fakten melden; keine Behauptung einer ausgeführten Hardwareinstallation.

## Bestandteile der integrierten Quellcodebasis

Die folgenden Komponenten existieren bereits in der heutigen Source-Historie und werden über den Fast-forward **ohne Neuentwicklung** übernommen:

| Bereich | Bereits vorliegende Umsetzung / Dateien | Verifizierungsgrenze |
|---|---|---|
| Offline Windows10-Grundlage | `src/mcm_solarcheck/offline/`, `src/mcm_solarcheck/gui/`, `scripts/start_windows10_offline.ps1`, `scripts/validate_windows10_offline.ps1`, `INSTALLATION.md` | CI auf GitHub-Windows-Runnern ≠ Nutzerhardware, kein Installer-Release |
| DJI M3T-Import | `src/mcm_solarcheck/importers/`, lokale Original-/ZIP-Importpfade, Datenmodelle | 33 RGB/160 Thermal sind Testübergabe, kein vollständiger Flugdatensatz |
| Thermal-Rohwerte | `src/mcm_solarcheck/thermal/`, Raw-16-Prüfpfad | Ohne unabhängigen Kalibrierungsnachweis keine °C-/Defektfreigabe |
| RGB Feature/Overlap | `orthomosaic_rgb_feature_matcher.py`, `orthomosaic_rgb_overlap_project.py`, `flight_rgb_link_run.py` | Bildmatcher liefert keine metrische Kamera-/Modulpose |
| RGB Diagnose / Segment-Vorschau | `orthomosaic_rgb_stitch_preview.py`, `flight_rgb_all_segments.py`, `rgb_project_preview_vertical.py`, `rgb_project_preview_cli.py` | Rein nichtmetrisch; der 2-Bild-Projektweg ist synthetisch getestet, **noch keine Windows-GUI-Integration** |
| Geneigte RGB-Dachflächen | `module_plane_basis.py`, `module_camera_calibration_gate.py`, `module_plane_rectification.py`, `rgb_surface_pilot_run.py` | Oberflächenebenen, Kamera-Intrinsics/Pose und Vermessungs-/Kontrollpunktnachweise erforderlich |
| Georaster/Orthofoto-Bausteine | `orthophoto_planar_rectification.py`, `orthophoto_planar_mosaic.py`, `orthophoto_planar_export.py`, GeoTIFF-Verträge | Nur mit explizit **unabhängig vermessener** Ebene/Kontrollpunkten freigeben |
| Review/Report/Export | Projekt-/Review-/Report-Pfade, testsichere Fachfreigabe-Gates | Kein automatischer Durchlauf mit bestätigten Modulen/Defekten; Freigabe fail-closed |

Die drei `experiment/two-agent-*` Zweige bleiben **unverändert separat**. Ihre Nicht-Übernahme als Branchcommit ist absichtlich: die gegenwärtige aktive Linie enthält bereits ihren eigenen Export-/Datenschutztest und die fortgeschriebene GUI. Der damalige rote unabhängige QA-Lauf und die erfolgreichen experimentellen UI-/Review-Läufe sind im Branch-Katalog dokumentiert. Keine unbelegte Behauptung bytegleicher Quellfunktionen.

## Windows-10-Offline-Abnahme: offenes Release-Gate

Das Übernehmen nach `main` ist nur **Codeintegration**. Eine eigenständige vollständige und für reale PV-Diagnose freigegebene Offline-Version erfordert vor Freigabe:

1. **Windows-10-Rechner** mit **explizit separatem neuen Checkout/virtueller Umgebung**, keine automatische Änderung am bestehenden lokalen Piloten; lokale startbare UI, Fehleranzeigen, Projekte, sicheres Beenden/Abbrechen.
2. Wiederholbarer Importlauf mit *zulässigem lokalen Testdatenbestand*; Import-/Rohbyte-Prüfsummen unverändert; erneuter Projektstart und persistierter Status; Test-/Produktivdatenbanken strikt getrennt.
3. **Vertikale RGB-first-Lücke schließen:** Projekt → RGB-Primärbilder → nutzbarer GUI-Aufruf → sichtbare lokale Vorschau mit Status/Abbruch → unabhängig kalibrierte geneigte Dachfläche → gemessenes echtes RGB-Flächenmosaik mit Coverage, Fehler- und Kalibrierungsbelegen. Vorschau allein kein Orthofoto.
4. Erst danach RGB/IR-Kopplung mit unabhängiger Sensorpose/Verzeichnung, zeitlicher Paarung, eigenem radiometrischem Raster und registrierungsgeprüftem Thermalbild. Keine Temperatur- oder Fehlerbehauptung ohne Kalibrierung/Review.
5. Erst nach vollständigem verifizierten Verarbeitungslauf Experten-Review und Berichtsexport; fehlende Eingangsbilder/Flächen müssen als **partiell** angezeigt werden.
6. Netzfreiheit und kundenseitige Datensouveränität sowie Speicherbegrenzungen und Lizenzgrenzen überprüfen; keine stillschweigende ODM/WebODM-/Docker-/Cloud-Abhängigkeit. Installation/Upgrade erst mit separater Zustimmung.

## Verbindliches Vorgehen für jeden weiteren Entwicklungsschritt

- **Nur einen vertikalen Benutzerweg pro Schritt** fertigstellen, statt weitere lose Service-Dateien ohne Oberfläche zu schaffen.
- Vor Arbeit [Bestandsaufnahme](REPOSITORY_BRANCH_INVENTORY_2026-10-26.md), [Startseite](PROJECT_START_HERE.md), [Register](DEVELOPMENT_STEP_REGISTER.md) und bestehende Tests lesen.
- Nach jedem Schritt **Entwicklungsregister, Vereinbarung, Chat-Handoff, RGB-Roadmap** aktualisieren und den letzten Commit wieder mit Python-/Windows-CI prüfen. Kein neuer Test der bereits belegten MPO-Metadaten ohne echten Anlass.
- `main` ab Fast-forward gemeinsame Integrationsbasis. Für neue Arbeit kleine isolierte Featurezweige erstellen und **erst nach CI-/Review-Gate** via nicht erzwungenem Fast-forward/PR nach `main` übernehmen. `main` nicht als unverifizierten Experimentierzweig verwenden.
- Kein GitHub-Commit ändert die alte lokale Windows-10-Installation. Kein Merge/Branchlöschung, keine Originalbild-/Produktivdatenbankänderung, keine fiktive Orthofoto- oder medizinisch klingende Fehlerfreigabe.

## Ausführung des Fast-forward und Absicherung von main

Am 26.10.2026 wurde `main` **ohne Force-Push** (geprüfter erwarteter HEAD) von `e523a30dff0cb6a17fc8d287289cadb9cbde28d8` nach `56d6bf22f178bf98dbcb38559824d03c9ce718f1` bewegt: **4019 Commit-Vorwärtsschritte**, 0 zurückliegende Commits; danach `compare(main...feature)` = **identical**. Präintegrations-CI für `56d6bf2`: [Python grün](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40364637228), [Windows grün](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40364637118), jeweils 3.11/3.12.

**Zusätzliche notwendige CI-Konsolidierung:** Die Windows-Push-Trigger enthielten zuvor nur `feature/offline-human-report-approval`. Der nachfolgende `main`-Entwicklungsschritt **DEV-INT-002** erweitert den Trigger auf `main` und behält den alten Branch bei. Der neue Dokumentations-/Workflow-Commit muss danach separat alle erforderlichen Tests bestehen; eine frühere grüne CI reicht nicht.

## 26.10.2026 – DEV-RGB-GUI-001: RGB-Vorschau erstmals aus dem echten Projektbedienweg

**Quelle:** [Entwicklungsregister: DEV-RGB-GUI-001](DEVELOPMENT_STEP_REGISTER.md). Im isolierten `feature/offline-project-rgb-preview-gui` (von `main` `00c576b`) ist der bestehende RGB-Diagnose-Service an den Offline-Verarbeitungsbildschirm angeschlossen: echtes importiertes RGB-Paar wählen (keine manuellen privaten Pfade), explizit leeren lokalen Ordner auswählen, im abbruchfähigen QThread aus ausgewählten Originalen ein begrenztes PNG+JSON erzeugen, PNG im eindeutig **nichtmetrischen** Dialog präsentieren. Keine Überschreibung, kein DB-Schreiben, keine Thermal- oder Modulerkennung. Bei Projektwechsel oder nicht vorhandener Projektdatenbank wird fail-closed gehandelt. Der neue Qt-/Service-Test ist auch im Windows-CI-Workflow aufgenommen.

**Begrenzung:** 2 Bilder als **Vorschau**, keine Fläche/Modulhöhe/Pose aus DJI-GPS erfunden, keine Kamera-/Dachflächenkalibrierung und keine vollständige RGB-Orthofoto-Verifikation. Die vier bereits bekannten schwachen Verbindungen und hochgeneigte PV-Oberflächen werden nicht wegvalidiert. Die echte Windows-10-SC-0003-Abnahme bleibt offen. Finales GitHub-CI-Grün vor `main`-Integration prüfen; fehlgeschlagene Zwischencommits ehrlich behalten, nicht als Abschlusswert ausgeben.

**DEV-RGB-GUI-001 nachweislich in MAIN integriert (26.10.2026):** Fast-forward ohne History-Umschreibung von `main` `00c576b` auf `f1eaf5650ad7ad188afe22e93a61983bd040db44` (11 Commits). [Python-3.11/3.12-CI grün](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40370445214); [Windows-3.11/3.12-CI grün](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/40370445459). Aktuelle Offline-Anwendung enthält damit die projektgebundene PNG+JSON-RGB-Vorschau aus zwei bereits importierten Bildern, GUI-Bilddialog, Fortschritt und kooperativen Abbruch. Geltungsgrenze: synthetische Automatisierung, **nicht** echte Windows-10-Pilotabnahme, nicht metrische Orthorektifizierung. Nächster Schritt ist kontrollierte Windows-10-Abnahme, keine erneute MPO-Inventur. Quelle: [Register DEV-RGB-GUI-001](DEVELOPMENT_STEP_REGISTER.md).
