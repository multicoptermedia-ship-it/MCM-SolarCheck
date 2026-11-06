# ODM-Workflow als Vergleich für SolarCheck – 06.11.2026

Der Nutzer hat den Vergleich mit [Open Drone Map: Structure-from-Motion Workflow](https://www.researchgate.net/publication/370057094_Open_Drone_Map_Structure-from-Motion_Workflow) ausdrücklich angeregt. Das öffentlich zugängliche Methodenpapier von Valorie Marie, Andrii Zaiats, Ryan Wickersham und Trevor Caughlin (16.04.2023, [DOI 10.7923/92HF-GP09](https://doi.org/10.7923/92HF-GP09)) wurde gelesen. Kein PDF/Fremdcode wird ins Produkt übernommen. Der Vergleich hebt die bestehende ODM/WebODM/ODX-Integrationssperre nicht auf. [Verbindlicher Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

## Was das Dokument tatsächlich behandelt

Die Anleitung nennt die native Windows-Anwendung WebODM 2.8.4–2.8.8. RGB-Beispiel: DJI Mavic 2 Pro, DNG→JPG, Metadatenerhalt, im Gelände vermessene GCPs, Orthomosaik/DSM/Punktwolke. Zweiter Sensor: DJI Phantom 4 Multispectral; dessen Reflexionskorrektur und Vegetationsindizes sind kein radiometrischer Thermal-/Celsiusworkflow für DJI M3T. Die Anleitung erwähnt TIFF-Unterstützung für Thermaldaten, arbeitet aber keinen M3T-RJPEG-/Celsiusablauf aus. GCP Editor Pro und weitere Hilfsprogramme werden beschrieben; daraus folgt keine freigegebene oder notwendige SolarCheck-Komponente.

Die Einstellungen sind fallbezogen. Beispielsweise werden hohe Merkmalszahlen, eine bestimmte Tiefenkartenauflösung und auf den Flug bezogene Ausgaberaster genannt. Das ist keine universelle Parameterempfehlung für unsere Kamera, unseren Rechner oder PV-Dächer. Die Anleitung rechnet ausdrücklich mit langen Laufzeiten bis zu Tagen.

## Vergleich mit vorhandenen SolarCheck-Bausteinen

| Workflow-Aspekt | Aussage der Anleitung | Konsequenz für SolarCheck |
| --- | --- | --- |
| Originale/Metadaten | DNG-Konvertierung und anschließender GPS-Metadatentransfer im RGB-Beispiel | M3T-JPGs liegen bereits vor. Vorhandenen Import und bytegleiche Arbeitskopien nutzen; keine Konvertierung, Originalumbenennung oder Metadatenüberschreibung hinzufügen. |
| Lagebezug | Vermessene GCPs, bewusst gewähltes Koordinaten-/Höhensystem | Kamera-GPS/RTK ist kein Ersatz für unabhängige Kontrollpunkte. Vorhandene Offline-Projektion/Positionsabgleich/GeoTIFF-Prüfung weiterverwenden; keine allgemeine GCP-/externe RGB-Kalibrierungspflicht für den Bildaufbau einführen. Lagegenauigkeit bleibt ungeprüft. |
| Kamerageometrie/Oberfläche | SfM und Oberflächenprodukte vor dem Orthomosaik | Diese Standardstufen existieren im COLMAP/OpenMVS-Pilot bereits. Falsche Bildzuordnungen lassen sich nicht durch einen CRS-Header beheben; keine eigene Engine nachbauen. |
| Produktumfang | Orthomosaik/DSM/Punktwolke; optionaler 3D-Modell-Export wird im Beispiel übersprungen | Produktziel bleibt RGB- und Thermal-GeoTIFF. Ein externes Werkzeug darf intern ein Oberflächenmodell für die Dachentzerrung benötigen; ein ausgeschalteter 3D-Produktexport ersetzt diese Geometrie nicht. |
| Zweiter Sensor | Multispektrale Reflexionskalibrierung und Vegetationsindizes | Nicht als M3T-Temperaturkalibrierung übernehmen. Thermal-Geometrie und Werteerhalt separat prüfen; Falschfarben/mittiger Temperaturpunkt sind keine verifizierte Celsiusmatrix. |
| Abnahme | Ergebnisprodukte und Verarbeitungsinformationen sichern | Vorhandenen GeoTIFF-Import, Rasterübersicht, PV-/Thermal-Zuordnung weiterverwenden. Vollständigkeit, Modulränder, Nähte und Sensorlage am tatsächlichen Ergebnis prüfen; kleine Pixelreste/CI allein reichen nicht. |

## Aktueller 287-Bilder-Abbruch ist zunächst ein Betriebsbefund

Der Screenshot vom 06.11. zeigt **COLMAP-Bildabgleich**, `step-08.log`, NVIDIA aus. Der Kamerarekonstruktionsschritt und OpenMVS wurden in diesem Lauf noch nicht erreicht. Daraus folgt keine Aussage über die mögliche Orthofotoqualität der vollständigen Serie.

Im aktuellen Pilot ist `exhaustive_matcher` eingestellt: Bei 287 Bildern sind maximal `287×286/2 = 41.041` ungeordnete Bildpaare möglich, gegenüber 325 bei 26 Bildern. Mehr Bilder können die Zuordnung stützen, erhöhen beim vollständigen Paarvergleich aber den Rechenaufwand stark. Das ist keine verlässliche Laufzeitprognose.

Der Starter begrenzt jede Rechenstufe auf **21.600 Sekunden = sechs Stunden** und zeigt Zeitlimit/Prozessfehler bisher gleich als generischen Abbruch an. Ein erreichtes Zeitlimit ist deshalb eine **Hypothese**, keine festgestellte Ursache. Benötigt werden `seconds`/`status` aus dem Eintrag `COLMAP-Bildabgleich` in `laufzeiten.json` und gegebenenfalls wenige bereinigte Fehlerzeilen aus `step-08.log`. Keine vollständigen Rohprotokolle, Kamerakoordinaten oder Kundendateien übertragen. Arbeitskopien und berechnete Daten erhalten, keinen Neustart anfordern, bevor die Ursache geklärt ist.

## Nächste technische Entscheidung nach dem Fehlerbefund

1. Zeitlimit, nativen Programmfehler und Ressourcenfehler unterscheiden. Bei Zeitlimit wäre eine verständliche Fehlermeldung plus gezielte Wiederaufnahme vorhandener Arbeit wichtiger als ein weiterer kompletter Neuimport. Kein pauschales Entfernen aller Grenzen oder Wiederholen desselben Vollvergleichs.
2. Für größere Serien prüfen, ob etablierte räumliche Bildpaar-Auswahl mit vorhandenen Werkzeugen geeignet ist. Ergänzende aktuelle Primärquellen: ODM beschreibt GPS-Nachbarschaft beziehungsweise Triangulationsauswahl; OpenSfM unterstützt räumliche/zeitliche Kandidatenauswahl. Das sind zusätzliche Quellcodebefunde, keine im Methodenpapier nachgewiesenen Einstellungen des Nutzerprojekts.
3. COLMAP 3.12.6 bietet selbst `spatial_matcher` mit `SpatialMatching.max_num_neighbors`, `max_distance` und `ignore_z`. Vor Nutzung müssen geeignete Positionsprioren in der tatsächlichen lokalen COLMAP-Datenbank und sinnvolle Abdeckung geprüft sein. Keine selbst programmierte Nachbarschafts-/Matching-Engine, kein blindes Übernehmen von Standardabständen oder ungesicherter GNSS-Genauigkeit. Noch kein solcher Lauf oder Implementierungswechsel erfolgt.
4. Erst nach vollständigem geometrischem Verbund die vorhandene Entzerrung/OpenMVS/GeoTIFF-Kette ausführen und reale Qualität prüfen. Keine Auswahl eines größten Teilmodells als Gesamtergebnis. Bestehende Referenz bleibt unabhängig manuell; keine ODM-Prozesse/API/Container/Installation aus SolarCheck.

## Ergänzende Primärquellen

- [COLMAP-3.12.6 SpatialMatching-Optionen](https://github.com/colmap/colmap/blob/3.12.6/src/colmap/controllers/option_manager.cc), [SpatialMatchingOptions](https://github.com/colmap/colmap/blob/3.12.6/src/colmap/feature/pairing.h).
- [ODM-Optionsbeschreibung, geprüfter Quellstand 681350f9](https://github.com/OpenDroneMap/ODM/blob/681350f9f9f06cf1c19ad0e8d1b0211eda2261fd/opendm/config.py).
- [OpenSfM-Matching-Konfiguration, geprüfter Quellstand caf3e8f6](https://github.com/mapillary/OpenSfM/blob/caf3e8f6a3a82af83114d3b58a41dcb3a51a0540/opensfm/config.py).
- Eigener Starter: [Prozessgrenze/Fehlerbehandlung/Matching-Aufruf](../src/mcm_solarcheck/services/colmap_openmvs_pilot.py).

Nur öffentliche Literatur/Quelltexte und bereits vorliegende sichere Statusangaben geprüft. Keine Kundenbilder/GPS/produktive SQLite verarbeitet, keine Fremdsoftware installiert oder Photogrammetrie ausgeführt. Dieser Vergleich ist keine RGB-/Thermal-/Windows-10-Fachabnahme.
