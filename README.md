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

Die Import-, Radiometrie-, Lokalisierungs-/Priorisierungs- sowie Modell-/Trainingsdatenverträge bis einschließlich Phase 8 sind testgestützt aufgebaut. Phase 9 ist abgeschlossen und ergänzt den backend-neutralen Inspektionsbericht, Review- und Release-Gates, Bild-/Temperatur-Provenienz, deterministische Report-Assets sowie den gemeinsamen DOCX-/ODT-/PDF-Export. Modellklassifikation bleibt ausdrücklich eine überprüfbare Empfehlung; die fachkundige menschliche Prüfung bleibt die maßgebliche Befundentscheidung. Ein wissenschaftlich validiertes Produktionsmodell, die Prüfung gegen die lizenzierte Norm und die kommerzielle Softwarefreigabe bleiben eigenständige Gates.


## Nächster Arbeitsblock

Phase 10 wird aus einer Bestandsaufnahme der vollständigen Projektpipeline abgeleitet. Vorrang haben Integrations- und Betriebsreife-Lücken zwischen Projektanlage, Import, Verarbeitung, Review und Berichtsexport; neue Komfortfunktionen werden erst danach eingeplant.

Die Desktop-GUI auf Basis von PySide6 wird in den folgenden Schritten als eigener, dokumentierter Bedienvertrag definiert. Ihre Navigation und Zustände sollen die fachlichen Pipeline- und Review-Gates abbilden und diese nicht umgehen. Preisstaffel und automatischer Flugplaner bleiben bis nach der technischen Kernpipeline zurückgestellt.


## Offline-Distribution (späte Release-Phase)

Für die Windows-Offline-Version wird zum Abschluss ein eigenes Installationsprogramm erstellt. Es soll die freigegebene SolarCheck-Anwendung und alle für den Offline-Betrieb notwendigen Laufzeitkomponenten reproduzierbar installieren, einschließlich der lokalen Projektdatenbank bzw. ihrer Initialisierung und Migration. Die Installation darf keine fachlichen Review-, Provenienz- oder Release-Gates umgehen.

Die Packaging-/Installer-Arbeit wird bewusst von der laufenden Kernentwicklung getrennt und erhält einen eigenen GitHub-Zweig. Dieser Zweig wird erst auf Basis eines stabilen Release-Kandidaten aufgebaut; konkrete Installer-Technologie und gebündelte Drittkomponenten werden anhand der dann tatsächlich benötigten Runtime-, Lizenz- und Offline-Anforderungen festgelegt.


## Post-release communication

After the SolarCheck project is completed and the release scope is verified, prepare
a concise teaser/spoiler for LinkedIn and customer communication. It should highlight
the final, actually delivered key features and create curiosity without promising
features that did not make the release. Marketing copy is a post-release task and
must be derived from the verified product state.
