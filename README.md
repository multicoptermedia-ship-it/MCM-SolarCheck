# MCM-SolarCheck

Automatisierte PV-Anlagenprüfung aus georeferenzierten RGB- und Thermaldaten.

## Ziel

MCM-SolarCheck soll RTK-georeferenzierte Einzelbilder kleiner und mittlerer PV-Anlagen importieren, für geeignete Dachanlagen ein Orthofoto erzeugen, RGB- und Thermaldaten KI-gestützt auswerten und einen editierbaren deutschsprachigen Prüfbericht als ODT/PDF erzeugen.

Für große Freiflächenanlagen kann ein vorhandenes Orthofoto als Eingang verwendet werden.

## Geplante Pipeline

1. Projekt anlegen und Bilder importieren
2. Metadaten/RTK-GPS aus EXIF/XMP auslesen und validieren
3. Orthomosaik für kleine/mittlere Dachanlagen erzeugen
4. PV-Module segmentieren/detek­tieren
5. Thermische und visuelle Anomalien erkennen
6. Ergebnisse georeferenzieren und nach Schweregrad priorisieren
7. Ergebnisse manuell prüfen und korrigieren
8. Zustandsbericht als ODT und PDF exportieren

## Technische Leitidee

- Python 3.11+
- PySide6 für die Desktop-Oberfläche
- OpenCV/Pillow/rasterio/GDAL für Bild- und Geodaten
- OpenDroneMap/WebODM bzw. kompatible Photogrammetrie-Pipeline für Orthofotos
- Ultralytics YOLO für Detektion/Segmentierung
- U-Net/ähnliche Modelle für pixelgenaue Segmentierung, soweit für den jeweiligen Defektdatensatz sinnvoll
- GeoPackage/SQLite für Projekte, Befunde und Geometrien
- python-docx/pandoc oder LibreOffice-Headless für editierbare Dokumente und PDF-Erzeugung

## Wichtiger Hinweis

Die KI-Erkennung ist als Assistenzsystem zu behandeln. Eine automatische Klassifikation ersetzt nicht die fachkundige Prüfung. Die konkrete Befund- und Berichtlogik wird an die gültige Ausgabe der DIN IEC/TS 62446-3 (VDE V 0126-23-3) und die tatsächlich verwendeten Messbedingungen angepasst.

## Status

Die Import-, Radiometrie-, Lokalisierungs-/Priorisierungs- und Phase-7-Modell-/Trainingsdatenverträge sind testgestützt aufgebaut. Phase 7 hält Modellklassifikation ausdrücklich als überprüfbare Empfehlung: Trainingsdaten benötigen menschliche Ground Truth und Rechtefreigabe, Modellartefakte bleiben über Dataset/Snapshot/Weights nachvollziehbar und die fachkundige Prüfung bleibt die maßgebliche Befundentscheidung. Das Repository wird weiter zur produktionsfähigen Desktop-Anwendung, zu validierten Modellen und Installationspaketen ausgebaut.
