# AKTUELLER ENTWICKLUNGSSTAND – MCM-SolarCheck

**Verbindlicher Erstlesepunkt. Zusätzlich [AGENTS.md](../AGENTS.md), [Anforderungen](ANFORDERUNGEN_ORTHOFOTO_CODEX.md) und [Werkzeugprüfung](FREIE_ORTHOFOTO_WERKZEUGE.md) lesen. Neueste Nutzeranweisung hat Vorrang.**

## Auftrag und Grenzen
Benötigt werden **ein RGB-Orthofoto und ein Thermal-Orthofoto**, georeferenziert als zweidimensionale GeoTIFFs, danach PV-Modulprüfung und Thermal-Zuordnung. Bewährte freie Standardsoftware verwenden; **keine neue Photogrammetrie-Engine**, kein eigener SfM-/BA-/Stitch-/Dachalgorithmus. Externe Programme dürfen intern Oberflächenmodelle berechnen.
Aktiv: `multicoptermedia-ship-it/MCM-SolarCheck`, Feature-Branch `feature/orthofoto-license-neutral-rgb-first-20261028`, Draft **PR #9**. Nutzer hat frühere Nur-Lese-Sperre aufgehoben. SolarCheck 2 unverändert lassen. **Kein Merge/Push nach `main`.**
**Windows 10 bleibt verbindlich.** Offline zuerst, Online danach mit gemeinsamem Python-Fachkern. Keine proprietären/kostenpflichtigen Orthofotoprogramme; Nutzer-Ausnahme 07.11.: Microsoft-C++-Buildtools/SDK nur für OpenSfM-Build. Keine ODM/WebODM/ODX-Anbindung, Prozesse, APIs, Container oder Paketierung. Eigenständiges manuelles WebODM außerhalb SolarCheck bleibt erlaubt; echte GeoTIFFs können über den vorhandenen Import übernommen werden.
Originalbilder/GPS/RTK/Kundendaten/produktive SQLite/Backups/private Raster nicht in GitHub/CI/Codex/Cloud verarbeiten. Standardmäßig nur Quellcode/synthetische Tests; keine autonome ZIP-/EXIF-/ORB-Inventur. Echte Verarbeitung nur lokal nach bewusstem Nutzerstart, Arbeitskopien außerhalb von Originalen/Git; Originale read-only. Gezeigte Screenshots sind keine Erlaubnis zum Laden weiterer Originalarchive.
**DEV-RGB-ORTHO-ENGINE-001: 3D-Entwicklung bis auf Weiteres einfrieren.** Eigene Photogrammetrie bleibt eingefroren. Nutzer nennt am 04.11. eigene Engine oder anderes freies Programm als Möglichkeiten; keine ausdrückliche Wiederaufnahme angeordnet. Nutzer bestätigt am 04.11. den COLMAP/OpenMVS-Pilot; spätere Online-Anpassung berücksichtigen, Offline zuerst.

## Vorhandene Teile – nicht erneut bauen
- **DEV-EXTERNAL-ORTHOPHOTO-PAIR-001:** Schema22, GeoTIFF-/GIS-Prüfung, atomare RGB-/Thermal-Paare, PV-Vorschläge/GIS-Zuordnung. metadata_only/Rohwerte/Falschfarben ohne Fach-/Celsiusfreigabe.
- **VERT-01A a4d1e941:** zentrale Rasterübersicht, Paarauswahl, Überblendung/Zoom, Wiederöffnung/Projektwechsel; Modulbeobachtungen eigener Reiter.
- **VERT-01B1 1a9d0c31:** vorhandener manueller Paarimport → Anlagenübersicht, eigene Erzeugung eingefroren.
- **VERT-01B2 dd8ed5c1:** MicMac → GeoTIFF-Paar → Übersicht technisch vorhanden, nach Qualitätsfehlschlag zurückgestellt, Code erhalten.
F:-Python/SQLite/ZIP-Start gemäß AGENTS erhalten. Historische Technik920ba8f2 Linux/Windows inkl.Tk grün; keine Bildabnahme.

## Nutzerbefund und Priorität
**MICMAC-REAL-02 FAIL:** zwei unbrauchbare Praxistests, zweite Dachanlage mit RTK laut Nutzer. MicMac/RGB-POSE-01 zurückgestellt; keine neuen Parameter-/Maskenläufe. Kein generelles Urteil über MicMac.
**ALT-ORTHO-01:** Nutzer bestätigt lokalen COLMAP/OpenMVS-Pilot. 287er-Fortsetzung am 07.11. ohne einzelne Kameralösung beendet, Pilot zurückgestellt; keine Haupt-GUI-Anbindung. Keine neue Engine oder private Original-/DB-Verarbeitung hier.

## Konkreter nächster Einstieg – 09.11.2026 OpenSfM-GPU-Funktionsprobe
**OPEN-SFM-REVIEW-01:** [Quellenprüfung](OPENSFM_PRUEFUNG_2026-11-07.md): neuer v1.1/8b6b77ef-Zweig hat eigenen RGB-GeoTIFF-Weg; run_all.bat unvollständig. Alter Mapillary-Zweig kein gleicher GeoTIFF-Nachweis. Keine Engine-Neuentwicklung.
**OPEN-SFM-OPENCL-01 PASS Nutzer07.11.:** MX250/CL1.2/Treiber417.49,2 GiB VRAM/max512 MiB je Allokation, kleiner Kernel bestanden; Intel ebenfalls PASS. Kein OpenSfM-/Lasttest, nicht wiederholen.
**MSVC-SDK-01 PASS Nutzer08.11.:** C++17/WindowsSDK/x64 bestanden, VS17.14.37827.9. C28 GB frei, Cleanup beendet. QGIS/Plugins/Profile/Arduino/F:-Python/SQLite erhalten.
**OPEN-SFM-ENV-01 real PASS Nutzer08.11.:** Python3.10.22,22 isolierte Importe, GeoTIFF verfügbar/PROJ-Netz aus. E:\SolarCheck-OpenSfM\env und [fester Lock](../config/opensfm/conda-win64-explicit.lock) eingerichtet; nicht neu installieren/entfernen.
**OPEN-SFM-BUILD-01 real PASS Nutzer09.11.:** solarcheck-opensfm-build-1/status passed,9 native Module, native_constant_check passed, command_registry available. dataset/gpu_execution not_tested. VS17.14.44/vcvars x64 initialisiert. Quellbau/Installation abgeschlossen; Starter nicht wiederholen. CI42517970232 v1.1/8b6b77ef-Quellbau/OpenCL PASS. Git128-Besitzfix abgeschlossen: zwei genaue Prozessfreigaben, keine globalen Änderungen. Besitzfix0979499a auf Windows3.11/3.12 PASS; Docse81bfe80 alle CI grün. Vorhandene Buildordner/Umgebung erhalten.
**OPEN-SFM-GPU-02 real FAIL Nutzer09.11.:** system32_preload/0xC0000005, structured_result_written true und last_stage worker_complete. Worker hat JSON und Abschlussmarke geschrieben, Exit danach fehlerhaft. Teilberichtsinhalt fehlt: weder erfolgreiche Geräteabfrage noch GPU-Erkennung behaupten; kein Matching gestartet. Cleanup-/Finalisierungsproblem wahrscheinlich, konkretes Modul/Ursache unbekannt. Keine weitere Loader-/Treiber-/Hardwarevariation auf Verdacht.
**Windows-Absturzmodul erhalten:** zwei identische Treffer ntdll.dll10.0.19041.6456/0xC0000005/Offset0000000000024785. Das ist die Erkennungsstelle, kein Beleg für defekte Windows-DLL/Treiber/Hardware. Windows-Abfrage abgeschlossen, nicht wiederholen.
**OPEN-SFM-GPU-03 vorbereitet:** einmal regulärer Upstream-Einstieg opensfm.commands vor nativen APIs (--cli-imports), System32-Modus unverändert. MPL/Temp E:/PROJ-Netz aus, Prozesswerte zurücksetzen; keine DataSet-/Bilder-/Jobs/Engineänderung.30 s/Worker,64 künstliche Deskriptoren nur nach sauberem Inventarexit; Teilbericht bleibt Diagnose, Crash FAIL. Lokal24 Adaptertests PASS; Startblock/Windows-/Nutzerbefund offen, neues Feld startup_mode official_cli. Bei weiterem Fehler keine Variantenserie; nativen Stack eingrenzen. Build geschlossen; RGB-Pilot danach, bestehende GeoTIFF-/PV-Kette, Dense/Thermal/Qualität offen.
**THERMAL-REFERENCE-01:** RGB-/Thermalpaar benannt; Thermal-Vorschau links Dach erkennbar, rechts Verziehungen/Fragmente/Lücken, nicht auswerten. RGB-Thumbnail404, kein visueller Paarvergleich; kein weiterer Dateilink nötig. Original-TIFF/CRS/Werte/Registrierung ungeprüft, Zuschneiden repariert keine Geometrie. Keine Dateien/Drive-IDs/Kundenpfade nach Git. Vorhandenen GeoTIFF-/PV-Weg erhalten.
**Thermal bleibt Pflicht, für den Kandidaten ungeklärt:** eigene Sensorparameter/geometrische Zuordnung und Werteerhalt; keine RGB-Intrinsics kopieren oder Celsiuswerte aus Falschfarben/Temperaturpunkt ableiten. OpenMVS-Texturierung ist keine radiometrische Kalibrierung. Ein guter RGB-Pilot allein erfüllt den Auftrag noch nicht.
Abnahme: vollständige Dach-/PV-Flächen, scharfe zusammenhängende Modulränder, keine versetzten Stücke/Doppelkonturen, belegte Georeferenz, vertretbare gemessene Laufzeit, anschließend räumlich passendes Thermal. Danach vorhandene PV-/Thermal-/Review-/Berichtskette verbinden. **VERT-01 insgesamt fachlich weiterhin nicht abgenommen.**

## Frühere Befunde – nicht wiederholen
Erste 26/26-Serie ohne RTK separat halten: RGB/Thermal FAIL. PNG-/Cache-/GrShade-/Dateisuche abgeschlossen, keine Wiederholung/Originaldateianforderung. Details im Register; keine Kundendaten/Links in Git.

## Verbindliche vertikale Chat-Übergabe
Start: AGENTS, Checkpoint, Anforderungen/Register lesen; lokalen/Remote-HEAD und exakte CI prüfen. Am genannten offenen Teil fortsetzen, keine geschlossenen Funktionen erneut bauen.
Ende: zuerst diesen Checkpoint (1.000–8.500 Zeichen), dann Register/Vereinbarung/Handoff/Roadmap aktualisieren: Block-ID/Status, Commit/Testbelege, offene Lücke, genauer nächster Einstieg und Abnahme. Quellenprüfung, technische Tests und reale Fachabnahme getrennt kennzeichnen. CI allein ist keine Produktfreigabe. Praxis-PDF-Profil bleibt verbindlich; Original-PDFs nicht nach Git. VERT-02/Befund→Modul-ID→RGB-Vergleich→gespeicherte Entscheidung→Bericht danach; Online/Zahlung/Installer nachrangig.
