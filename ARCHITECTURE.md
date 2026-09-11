# MCM-SolarCheck – Zielarchitektur

## Pipeline

`RTK-Fotos -> Metadatenprüfung -> Orthomosaik -> Panel-Segmentierung -> RGB/IR-Kopplung -> Defekterkennung -> Georeferenzierung -> Fachprüfung -> ODT/PDF`

### 1. Projekt und Import

- Projektname und Kunden-/Anlagendaten
- Batch-Import von JPG/JPEG/TIFF
- EXIF/XMP/RTK-Positionen
- Aufnahmezeit, Kamera, GSD und Qualitätsparameter
- getrennte Verwaltung von RGB und Thermal

### 2. Orthofoto

Für kleine/mittlere Dachanlagen soll eine photogrammetrische Pipeline integriert werden. Die konkrete Engine wird so gekapselt, dass später OpenDroneMap/WebODM, MicMac oder eine vorhandene Unternehmenslösung austauschbar sind.

Für große Freiflächenanlagen bleibt der vorhandene Orthofoto-Workflow des Unternehmens als Eingang möglich.

### 3. Panel-Segmentierung

Ein Segmentierungsmodell identifiziert einzelne Module. U-Net/Mask-R-CNN oder YOLO-Segmentation sind mögliche Ansätze. Die Architektur soll Modellwechsel erlauben.

### 4. Defekterkennung

RGB und Thermal werden nicht blind in ein einziges Modell gesteckt. Stattdessen werden modality-spezifische Modelle und ein gemeinsames Befundschema verwendet. Das erlaubt unterschiedliche Modelle für:

- Hotspots / Überhitzung
- Bypass-/Diodenfehler-Muster
- Zell-/String-Anomalien
- Soiling / Verschmutzung
- Vogelkot
- sichtbare Glasbeschädigung
- Verfärbungen / Snail Trails
- Delamination-Hinweise
- fehlende/verschobene Module
- Verschattung / Vegetation
- weitere modellabhängige Klassen

Wichtig: Mikro-Risse, PID und bestimmte interne Zellfehler sind mit RGB/Thermal aus der Luft nicht zuverlässig vollständig sichtbar. Dafür können EL/PL/UVF-Daten bzw. elektrische Messungen erforderlich sein. Die Software muss deshalb zwischen **direkt aus Bilddaten erkennbar**, **Hinweisbefund** und **nicht mit dieser Datenbasis beurteilbar** unterscheiden.

### 5. Befunddatenbank

Jeder Befund bekommt:

- Projekt-ID
- Panel-ID
- Defektklasse
- Konfidenz
- Schweregrad
- Temperatur-/Kontrastwerte, soweit verfügbar
- GPS/Geometrie
- Quellbild und Crop
- Orthofoto-Position
- Modellversion
- Zeitstempel
- Fachprüfstatus
- Kommentar / Maßnahme

### 6. Bericht

Der Bericht wird als ODT erzeugt und kann über LibreOffice reproduzierbar nach PDF exportiert werden. Alle KI-Befunde müssen mit Bildnachweis und Modellversion nachvollziehbar sein.

## Modellstrategie

Es existieren bereits öffentlich zugängliche Forschungs-/Open-Source-Ressourcen. Beispiele sind ein großes thermisches PV-Defektdatenset mit über 23.000 Bildern, ein YOLO-Projekt für Hotspots/Diode-Fehler sowie weitere Datensätze für Hotspots und visuelle Defekte. Diese Quellen dürfen nicht ungeprüft als produktives Modell übernommen werden: Lizenz, Aufnahmebedingungen, Sensoren, Klassen, Ground Truth und Generalisierbarkeit müssen geprüft werden.

Für MCM-SolarCheck sollte deshalb ein eigenes, kuratiertes Validierungsset aus realen MCM-Dronetech-Aufnahmen aufgebaut werden.

## Qualität und Normbezug

Die Anwendung dokumentiert die für die Thermografie relevanten Aufnahmebedingungen und weist auf fehlende/ungeeignete Bedingungen hin. Die normgerechte fachliche Interpretation und Freigabe bleibt Aufgabe des qualifizierten Prüfers. Normtexte werden nicht im Quellcode reproduziert; die jeweils gültige Normausgabe und interne Prüfvorgaben sind maßgeblich.
