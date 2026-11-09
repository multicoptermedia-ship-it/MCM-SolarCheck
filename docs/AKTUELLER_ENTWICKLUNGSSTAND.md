# AKTUELLER ENTWICKLUNGSSTAND – MCM-SolarCheck

**Verbindlicher Erstlesepunkt. Zusätzlich [AGENTS.md](../AGENTS.md), [Anforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) und [Werkzeugprüfung](FREIE_ORTHOFOTO_WERKZEUGE.md) lesen. Neueste Nutzeranweisung hat Vorrang.**

## Auftrag und Grenzen
Benötigt werden **ein RGB-Orthofoto und ein Thermal-Orthofoto**, georeferenziert als zweidimensionale GeoTIFFs, danach PV-Modulprüfung und Thermal-Zuordnung. Bewährte freie Standardsoftware verwenden; **keine neue Photogrammetrie-Engine**, kein eigener SfM-/BA-/Stitch-/Dachalgorithmus. Externe Programme dürfen intern Oberflächenmodelle berechnen.
Aktiv: `multicoptermedia-ship-it/MCM-SolarCheck`, Feature-Branch `feature/orthofoto-license-neutral-rgb-first-20261028`, Draft **PR #9**. Nutzer hat frühere Nur-Lese-Sperre aufgehoben. SolarCheck 2 unverändert lassen. **Kein Merge/Push nach `main`.**
**Windows 10 bleibt verbindlich.** Offline zuerst, Online danach mit gemeinsamem Python-Fachkern. Keine proprietären/kostenpflichtigen Orthofotoprogramme; Nutzer-Ausnahme 07.11.: Microsoft-C++-Buildtools/SDK nur für OpenSfM-Build. Keine ODM/WebODM/ODX-Anbindung, Prozesse, APIs, Container oder Paketierung. Eigenständiges manuelles WebODM außerhalb SolarCheck bleibt erlaubt; echte GeoTIFFs können über den vorhandenen Import übernommen werden.
Originalbilder/GPS/RTK/Kundendaten/produktive SQLite/Backups/private Raster nicht in GitHub/CI/Codex/Cloud verarbeiten. Standardmäßig nur Quellcode/synthetische Tests; keine autonome ZIP-/EXIF-/ORB-Inventur. Echte Verarbeitung nur lokal nach bewusstem Nutzerstart, Arbeitskopien außerhalb von Originalen/Git; Originale read-only. Gezeigte Screenshots sind keine Erlaubnis zum Laden weiterer Originalarchive.
**DEV-RGB-ORTHO-ENGINE-001: 3D-Entwicklung bis auf Weiteres einfrieren.** Eigene Photogrammetrie bleibt eingefroren. Keine ausdrückliche Wiederaufnahme angeordnet. Offline zuerst, gemeinsame Fachlogik für Online erhalten.

## Vorhandene Teile – nicht erneut bauen
- **DEV-EXTERNAL-ORTHOPHOTO-PAIR-001:** Schema22, GeoTIFF-/GIS-Prüfung, atomare RGB-/Thermal-Paare, PV-Vorschläge/GIS-Zuordnung. metadata_only/Rohwerte/Falschfarben ohne Fach-/Celsiusfreigabe.
- **VERT-01A a4d1e941:** zentrale Rasterübersicht, Paarauswahl, Überblendung/Zoom, Wiederöffnung/Projektwechsel; Modulbeobachtungen eigener Reiter.
- **VERT-01B1 1a9d0c31:** vorhandener manueller Paarimport → Anlagenübersicht, eigene Erzeugung eingefroren.
- **VERT-01B2 dd8ed5c1:** MicMac → GeoTIFF-Paar → Übersicht technisch vorhanden, nach Qualitätsfehlschlag zurückgestellt, Code erhalten.
F:-Python/SQLite/ZIP-Start gemäß AGENTS erhalten. Historische Technik920ba8f2 Linux/Windows inkl.Tk grün; keine Bildabnahme.

## Nutzerbefund und Priorität
**MICMAC-REAL-02 FAIL:** zwei unbrauchbare Praxistests, zweite Dachanlage mit RTK laut Nutzer. MicMac/RGB-POSE-01 zurückgestellt; keine neuen Parameter-/Maskenläufe. Kein generelles Urteil über MicMac.
**ALT-ORTHO-01:** Nutzer bestätigt lokalen COLMAP/OpenMVS-Pilot. 287er-Fortsetzung am 07.11. ohne einzelne Kameralösung beendet, Pilot zurückgestellt; keine Haupt-GUI-Anbindung. Keine neue Engine oder private Original-/DB-Verarbeitung hier.

## Konkreter nächster Einstieg – 09.11.2026 OpenSfM/NVIDIA-Kompatibilität
**OPEN-SFM-REVIEW-01:** [Quellenprüfung](OPENSFM_PRUEFUNG_2026-11-07.md): neuer v1.1/8b6b77ef-Zweig hat eigenen RGB-GeoTIFF-Weg; run_all.bat unvollständig. Alter Mapillary-Zweig kein gleicher GeoTIFF-Nachweis. Keine Engine-Neuentwicklung.
**OPEN-SFM-OPENCL-01 PASS Nutzer07.11.:** MX250/CL1.2/Treiber417.49,2 GiB VRAM/max512 MiB je Allokation, kleiner Kernel bestanden; Intel ebenfalls PASS. Kein OpenSfM-/Lasttest, nicht wiederholen.
**MSVC-SDK-01 PASS Nutzer08.11.:** C++17/WindowsSDK/x64. C28 GB frei, Cleanup beendet. QGIS/Plugins/Profile/Arduino/F:-Python/SQLite erhalten.
**OPEN-SFM-ENV-01 real PASS Nutzer08.11.:** Python3.10.22/22 Importe/GeoTIFF/PROJ-Netz aus, E:\SolarCheck-OpenSfM\env/[fester Lock](../config/opensfm/conda-win64-explicit.lock). Nicht neu installieren/entfernen.
**OPEN-SFM-BUILD-01 real PASS Nutzer09.11.:** solarcheck-opensfm-build-1/status passed,9 native Module, native_constant_check passed, command_registry available. dataset/gpu_execution not_tested. Quellbau/Installation abgeschlossen, nicht wiederholen. v1.1/8b6b77ef, CI42517970232 PASS. Git128-Besitzfix abgeschlossen: zwei genaue Prozessfreigaben, keine globalen Änderungen. Buildordner/Umgebung erhalten.
**OPEN-SFM-GPU-03 real FAIL:** official_cli/system32_preload:1 GPU erkannt, dann0xC0000005/worker_complete. Kein Matching. Loader-/Importvergleiche abgeschlossen.
**OPEN-SFM-STACK-01 real Diagnose-PASS Nutzer09.11.:** Eigenprüfung passed, Inventar captured/0xC0000005,31 Frames/unwind_error0; pyfeatures/C-Runtime → mehrfach nvopencl64.dll → ntdll.dll/Offset24785. NVIDIA-OpenCL beim Prozessende beteiligt; konkreter Treiberfehler versus OpenSfM-Ressourcenlebensdauer nicht bewiesen. Statischer CLContext in unveränderter v1.1-Quelle passt zum Freigabezeitpunkt. Kein GPU-PASS/Matching; Stackdiagnose abgeschlossen, nicht wiederholen. Adapterc65ec558 alle drei CI-Läufe grün, echte Windows-Debugprüfung bestanden.
**OPEN-SFM-NVIDIA-01 abgeschlossen:** Nutzer bestätigt582.78 installiert/neu gestartet. Nicht erneut installieren. Neuer Lauf: inventory_failed/timeout/official_cli_imports; explizite Geräteabfrage/Matcher noch nicht erreicht. Weder Behebung des alten Absturzes noch GPU-Untauglichkeit daraus ableiten.
**OPEN-SFM-START-01 bereit:** [getrennte Import-/Native-Zeitfenster](OPENSFM_GPU_STARTZEIT_WINDOWS10.md). Bisher30 s für gesamten Worker inkl. großer CLI-Registry. Neuer optionaler Adaptermodus:120 s Importe, ab eigener lokaler Bereitschaftsdatei einmal30 s native Arbeit/Prozessende; wiederholte Marker verlängern nicht. Gleicher Loader/Importweg/Engine, keine zusätzliche Warmup-Probe oder Treiberänderung. timeout_phase/limit_seconds/last_stage, Originalexit verbindlich; kein Matching nach Inventarfehler.39 lokale Tests PASS. Quellec4a4d398/Windows42694877874: echte Prozess-/Pipe-/Dateisignal-/Timeoutfälle auf3.11/3.12 PASS. Hashstart bereit; Nutzerlauf offen. Neue Startdatei erhält alte GPU-/Stackprobe. Keine weiteren unveränderten Wiederholungen, keine Start-/Intel-/Treiber-Variantenserie. Geschlossene Nutzer-Toolchain nicht erneut prüfen/installieren. Bei weiterem bestätigtem GPU-FAIL Sparse→OpenMVS-CPU-Schnittstelle bewerten, kein Parallelpilot. RGB/Dense/Thermal/Georeferenz/Qualität offen.
**THERMAL-REFERENCE-01:** Paar benannt; Thermal rechts verzerrt/fragmentiert, nicht auswerten. RGB-Vorschau nicht verfügbar, kein weiterer Dateilink nötig. TIFF/CRS/Werte/Registrierung ungeprüft; Zuschneiden repariert keine Geometrie. Vorhandenen GeoTIFF-/PV-Weg erhalten.
**Thermal bleibt Pflicht, für den Kandidaten ungeklärt:** eigene Sensorparameter/geometrische Zuordnung und Werteerhalt; keine RGB-Intrinsics kopieren oder Celsiuswerte aus Falschfarben/Temperaturpunkt ableiten. OpenMVS-Texturierung ist keine radiometrische Kalibrierung. Ein guter RGB-Pilot allein erfüllt den Auftrag noch nicht.
Abnahme: vollständige Dach-/PV-Flächen, scharfe zusammenhängende Modulränder, keine versetzten Stücke/Doppelkonturen, belegte Georeferenz, vertretbare gemessene Laufzeit, anschließend räumlich passendes Thermal. Danach vorhandene PV-/Thermal-/Review-/Berichtskette verbinden. **VERT-01 insgesamt fachlich weiterhin nicht abgenommen.**

## Frühere Befunde – nicht wiederholen
26/26-Serie ohne RTK separat: RGB/Thermal FAIL. PNG-/Cache-/GrShade-/Dateisuche abgeschlossen; nicht wiederholen. Details im Register.

## Verbindliche vertikale Chat-Übergabe
Start: AGENTS, Checkpoint, Anforderungen/Register lesen; lokalen/Remote-HEAD und exakte CI prüfen. Am genannten offenen Teil fortsetzen, keine geschlossenen Funktionen erneut bauen.
Ende: zuerst diesen Checkpoint (1.000–8.500 Zeichen), dann Register/Vereinbarung/Handoff/Roadmap aktualisieren: Block-ID/Status, Commit/Testbelege, offene Lücke, genauer nächster Einstieg und Abnahme. Quellenprüfung, technische Tests und reale Fachabnahme getrennt kennzeichnen. CI allein ist keine Produktfreigabe. Praxis-PDF-Profil bleibt verbindlich; Original-PDFs nicht nach Git. VERT-02/Befund→Modul-ID→RGB-Vergleich→gespeicherte Entscheidung→Bericht danach; Online/Zahlung/Installer nachrangig.
