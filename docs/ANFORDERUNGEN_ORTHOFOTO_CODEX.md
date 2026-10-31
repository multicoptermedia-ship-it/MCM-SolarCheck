# Verbindliche SolarCheck-Anforderungen – freie Orthofoto-Standards und Codex

**Entscheidung vom 31.10.2026.** Hat Vorrang vor historischen SfM-/3D-/Orthofoto-Eigenentwicklungsplänen. Von Codex **vor jedem Arbeitsschritt** zusammen mit [AGENTS.md](../AGENTS.md) und dem [aktuellen Entwicklungsstand](AKTUELLER_ENTWICKLUNGSSTAND.md) zu lesen.

## Anforderungen

**REQ-ORTHO-01 · 2D-Ergebnis:** SolarCheck soll ein scharfes, vollständiges, korrekt georeferenziertes **zweidimensionales RGB-Orthofoto** als GeoTIFF nutzen. Kein 3D-Modell als Produkt. Ein etabliertes externes Programm darf intern die für echte Dach-Orthorektifizierung notwendige Perspektiv-/Oberflächenkorrektur ausführen.

**REQ-ORTHO-02 · Keine Neuentwicklung:** **Keine weitere selbst programmierte Photogrammetrie-, SfM-, Bundle-Adjustment-, 3D-Dach-, Stitching-, Orthorektifizierungs- oder Naht-Engine.** Standardimplementierungen verwenden. SolarCheck-Entwicklungszeit für **PV-Moduldetektion, Modul-IDs, RGB-/Thermal-Zuordnung, fachkundige Kontrolle und Berichte** reservieren.

**REQ-ORTHO-03 · Keine kommerzielle Lizenzsoftware:** Keine proprietären/kostenpflichtigen Programme, Abonnements oder temporären Testlizenzen (einschließlich **Agisoft Metashape Professional**). Nur kostenfreie Open-Source-Optionen; deren tatsächliche Lizenzen, Dritt-Abhängigkeiten und Weitergaberechte vor einer etwaigen Distribution prüfen. Keine automatische Installation oder Fremdsoftware-Ausführung ohne Freigabe.

**REQ-ORTHO-04 · Vorhandenes WebODM ist externe Option:** Der Nutzer **hat bereits WebODM**. Er darf es **eigenständig, manuell und unabhängig von SolarCheck** für die 2D-RGB-Orthofoto-Erzeugung verwenden. Ein extern erzeugtes RGB-GeoTIFF ist ein zulässiger Eingabedatensatz. **Keinesfalls ODM/WebODM/ODX-Code, APIs, Prozesse, Docker/Container, Dienste, Runtime oder Installer in SolarCheck integrieren oder automatisch aus SolarCheck starten.** Die bisherige Integrationssperre bleibt vollständig bestehen. Manuelle Dateiausgabe und anschließender Import sind **keine Integration**.

**REQ-ORTHO-05 · Freie Alternative:** [MicMac](https://github.com/micmacIGN/micmac) (IGN, Open Source) mit bestehenden Modulen **Malt Ortho** und **Tawny** ist eine *separate lokale Alternative*, falls der Nutzer sein vorhandenes WebODM nicht nutzen kann/will. MicMac-Windows-10-Kompatibilität für genau die DJI-M3T-Bilder ist **noch nicht lokal nachgewiesen**, nicht als garantiert darstellen. Standardbibliotheken **OpenCV, rasterio, pyproj** liegen bereits im SolarCheck-Stack; OpenCV Stitcher_SCANS nur nichtmetrische Vorschau, Rasterio/GDAL für bereits korrekt georeferenzierte Raster – **keine** „Orthofoto-Freigabe“ aus einer reinen Pixelhomografie oder Kamera-GPS.

**REQ-ORTHO-06 · Vorhandenen Import verwenden:** Die SolarCheck-Importseite bietet **„GeoTIFF / GIS-Metadaten prüfen“** und **„GeoTIFF dauerhaft im Projekt registrieren“**. RGB-GeoTIFF-Berichtsvorschau existiert. Diese Wege wiederverwenden, **keinen neuen Importer** bauen. GeoTIFF benötigt **tatsächlich belegten CRS/EPSG und Rastertransform**, keine geratenen Bodenkoordinaten, Kamerakalibrierungen oder künstlich gesetztes `georeferencing_verified=True`. Die Metadatenprüfung ist **keine** unabhängige geometrische Qualitätskontrolle.

**REQ-ORTHO-07 · Bereits bekannter Originalbestand:** Sechs private Hummintech-`.zip`/`.tip` enthalten **160 RGB-JPEGs der DJI M3T, 4000×3000**, sieben Flugstreifen. **Keine erneute Archiv-, EXIF-, ORB- oder Paar-Inventur.** Originalarchive ausschließlich read-only; bei separater lokaler Berechnung nur bewusst erstellte private Arbeitskopien.

**REQ-ORTHO-08 · Realqualitätsprüfung:** Der 160-Foto-Windows-Pilot vom 28.10.2026 ist **FAIL** (Einzelstreifen besser; Gesamtbild unscharfe PV-Module, Doppelkonturen/Geisterkanten, harte Nähte). Echte private 2D-Ausgabe muss vollständig und an denselben kritischen Bildstellen sichtbar verbessert sein; scharfe Modulränder, Abdeckung, Nähte und verifizierbare GeoTIFF-Referenz prüfen. **Keine** Vermessungs-, PV-ID-, Defekt- oder Thermal-Freigabe aus CI-/synthetischen Bildern oder einem TIFF-Header.

**REQ-ORTHO-09 · Privacy / offline / Codex:** Zielumgebung Windows 10; Kundenbilder, EXIF/GPS/RTK, private Bildvorschauen, produktive SQLite und Backups **nie** in GitHub/CI/Chat/Cloud/Codex-Kontext oder unkontrollierte Logs. Codex standardmäßig nur auf Quellcode und synthetische Tests begrenzen; nicht autonom private Bildordner lesen. Externer Rechenlauf nur unter Nutzerkontrolle in separatem privatem Verzeichnis. Codex ist selbst kein vollständig offline arbeitender Datenraum.

**REQ-ORTHO-10 · Projektsteuerung:** Codex zuerst `AGENTS.md`, diesen Anforderungen-Text und den aktuellen Checkpoint lesen; bestehende Funktionen zuerst prüfen, kleine Änderungen und passende Tests statt neue Architektur, schriftliche Übergabe und exakte HEAD-CI. **Kein Merge nach `main` ohne ausdrückliche Zustimmung**; PR #9 Draft, 3D-Eigenentwicklungszweig eingefroren.

## Nächster sinnvoller Schritt
**Zuerst das bereits vorhandene WebODM des Nutzers als manuelle externe Quelle** für ein korrektes RGB-GeoTIFF nutzen, sofern es für den privaten Flug funktioniert – ohne es in SolarCheck einzubauen. Falls nicht praktikabel, **MicMac extern prüfen**. Vorhandenen GeoTIFF-Import in SolarCheck verwenden und danach PV-Modul-IDs/Thermal entwickeln; keine weitere Eigenimplementierung der Orthofoto-Mathematik. **Noch kein** neu validierter vollständiger 160-RGB-Lauf in dieser Chat-Umgebung.

Siehe [externer GeoTIFF-Workflow](EXTERNES_RGB_ORTHOFOTO_GEOTIFF.md) und [dokumentierter Original-Fail](RGB_ARCHIVE_INTAKE_2026-10-28.md).
