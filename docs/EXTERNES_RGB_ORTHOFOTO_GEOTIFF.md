# Kostenfrei: bestehender Orthofoto-Algorithmus → 2D-RGB-GeoTIFF → SolarCheck

> **Codex-/Produktanforderungen:** [AGENTS.md](../AGENTS.md) und [ANFORDERUNGEN_ORTHOFOTO_CODEX.md](ANFORDERUNGEN_ORTHOFOTO_CODEX.md). Der Nutzer besitzt bereits **WebODM**; der schnellste Weg ist ein **rein manueller externer** RGB-GeoTIFF-Export, **ohne** SolarCheck-WebODM-Integration oder automatische Steuerung.

**Verbindliche Korrektur 31.10.2026:** Keine kostenpflichtigen oder proprietären Programme, auch keine Testlizenz. Agisoft Metashape Professional **nicht verwenden**. Open-Source-Programme sind ebenfalls lizenziert, aber normalerweise ohne Kauf-/Nutzungsgebühr: Bedingungen bei Nutzung und besonders Weiterverteilung prüfen. **Keine eigene Orthofoto-Rechenengine programmieren.**

## Vorhandenes in SolarCheck
- 160 bereits inventarisierte private DJI M3T RGB aus sechs ZIP/`.tip`-Originalarchiven mit GNSS/RTK; keine erneute Inventur, keine private Rohdatei/GPS/SQLite nach Git/CI/Cloud.
- Installierte Libraries `opencv-python-headless`, `rasterio`, `pyproj` sowie bereits implementierte Schaltflächen **„GeoTIFF / GIS-Metadaten prüfen“** und **„GeoTIFF dauerhaft im Projekt registrieren“**.
- RGB-GeoTIFF-Berichtsvorschau existiert. Diese Bausteine wiederverwenden, keinen neuen Importer schreiben.

## Erste Option: bereits vorhandenes WebODM – **nur separat/manuell**
Der Nutzer kann sein vorhandenes WebODM **eigenständig außerhalb von SolarCheck** zur Berechnung eines privaten RGB-Orthofotos einsetzen und das fertige **GeoTIFF** wie jede andere externe Rasterdatei in SolarCheck importieren. **Das ist keine Programmintegration:** ODM/WebODM/ODX niemals als SolarCheck-Code, Bibliothek, Service, API, Container, automatisch gestarteten Prozess, Runtime oder Installer-Abhängigkeit einbauen. Keine erneute Installation verlangen. Privatbilder bleiben im separaten lokalen Arbeitsbereich des Nutzers. Echtes CRS/Pixelgeometrie und sichtbare Bildqualität vor dem Import prüfen. In dieser Chat-Umgebung ist noch kein reales neues 160-RGB-Ergebnis entstanden.

## Zweite freie Option: MicMac vom französischen IGN
[MicMac](https://github.com/micmacIGN/micmac) ist kostenfreie Open-Source-Photogrammetriesoftware (CeCILL-B), mit Windows-10-Unterstützung. Für echte Orthofotos sind die dokumentierten Standardwerkzeuge [Malt Ortho](https://micmac.ensg.eu/index.php/Malt) (orthorektifizierte Einzelbilder nach vorhandener Kameraorientierung) und [Tawny](https://micmac.ensg.eu/index.php/Tawny) (Zusammenführung, optional radiometrischer Ausgleich) relevant. Das interne Oberflächenmodell ist ein mathematischer Rechenschritt; das **ausgegebene SolarCheck-Produkt bleibt zweidimensional**. **Nicht** selbst SfM, Bundle Adjustment oder einen Dachflächenalgorithmus schreiben.

**Technisch noch offen:** Ob das kostenfreie MicMac auf dem konkreten Windows-Rechner eingerichtet werden kann und die vorhandenen DJI-M3T-RGB-/XMP-/RTK-Daten korrekt interpretiert, ist **nicht** praktisch geprüft. Ein MicMac-TIFF kann ohne eingebettete CRS-/GeoTIFF-Information entstehen. Dann kein EPSG erfinden: erst tatsächliche Bild-zu-Boden-Referenz feststellen; nur korrekt referenzierte GeoTIFFs in SolarCheck registrieren.

**OpenCV-Stitcher nur für 2D-Vergleiche:** Der vorhandene [`cv2.Stitcher_SCANS`](https://docs.opencv.org/4.x/d8/d19/tutorial_stitcher.html) kann annähernd planare Bilder zusammensetzen, liefert bei verschieden geneigten Dächern aber **keine** garantierte Orthorektifizierung. [GDAL `gdalwarp`](https://gdal.org/en/stable/programs/gdalwarp.html)/`rasterio` mosaikieren/reprojizieren **bereits georeferenzierte Raster**; aus Kamera-GPS allein entsteht keine korrekte Dachortho-Geometrie.

## Schnellster abgesicherter Praxistest
1. Die bereits bekannten RGB-Originale **privat und read-only** halten; falls möglich das **bereits vorhandene WebODM manuell separat** benutzen, ohne SolarCheck daran anzuschließen. Nur wenn dieser externe Weg nicht geeignet ist, MicMac-Windows-Distribution/Toolchain und DJI-Kameratyp-Eignung prüfen; keine neuen Rechenmodule entwickeln.
2. Mit **einem repräsentativen Stück inklusive Streifenübergang** den gewählten externen Standardworkflow testen. Wenn Orientierung und Abdeckung stimmen, den vollständigen 160-RGB-Flug durchlaufen lassen. Keine erfundenen Kontrollpunkte, Objektivparameter oder Kartenkoordinaten.
3. **Nur 2D-RGB-Orthofoto** exportieren; echte CRS-/Rastertransform im GeoTIFF nachweisen. Scharfe PV-Modulränder und Doppelkonturen/Nähte am bisherigen fehlgeschlagenen Gesamtbild messen und visuell prüfen. Kein echtes Bild = kein Qualitäts-PASS.
4. Bestehende **SolarCheck Import → GeoTIFF prüfen → GeoTIFF registrieren** benutzen. Danach Zeit auf PV-Modul-IDs, Thermal und Berichte verwenden.

## Codex oder Chat?
Für **praktische Entwicklung am lokalen Windows-10-Rechner** Codex im lokalen Repository nutzen: Toolinstallation/-aufruf, gezielte Integration oder Tests statt wiederholter Chat-GitHub-only-Kommentare. Windows 10 unterstützt Codex nur im Best-Effort-Modus ([Codex Windows](https://learn.chatgpt.com/docs/app/windows)). Repo-Arbeitsverzeichnis von privaten Original-ZIPs trennen und Codex **keinen** Zugang/Upload zu Kundenfotos, GPS/RTK oder Analysebildern geben; Code- und Logausgaben auf sensible Daten prüfen. Lokal gestartete Codex-Aufgaben können trotzdem Kontext an den Dienst senden, daher kein umfassender Rohbildzugriff ohne gesonderte Datenschutzprüfung.

**Nicht ändern:** No-ODM/WebODM/ODX-Integration, keine kommerzielle Lizenzsoftware, keine neuen Photogrammetrie-Algorithmen, kein automatisches Main-Merge.
