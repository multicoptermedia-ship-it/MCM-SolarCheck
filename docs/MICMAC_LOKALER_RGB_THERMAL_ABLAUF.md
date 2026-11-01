# MicMac lokal: Einzelbilder → zwei Orthofotos → SolarCheck

Stand 01.11.2026 · Vorbereitung zu VERT-01B. Der SolarCheck-Teil „Verarbeitung → vorhandener Paarimport → Anlagenübersicht → Wiederöffnung“ ist angebunden. **Die folgende externe Berechnung wurde hier nicht ausgeführt.** Nutzer bestätigt: Auswerterechner bleibt unter Windows 10, kein Wechsel auf Windows 11; GUI/Projektanmeldung/Import wurden dort bereits getestet. Inzwischen gemeldeter MicMac-Pfad: `E:\Tools\MicMac\bin\mm3d.exe`. [Lokalen Starttest](MICMAC_WINDOWS10_EINRICHTUNG.md) durchführen; ein MicMac-Rechenlauf ist noch nicht bestätigt. Kein automatischer Download, Installer oder Prozessstarter; keine neue Photogrammetrie-Engine.

## Konkrete Werkzeuggrenze

Die vorhandene [Werkzeugprüfung](FREIE_ORTHOFOTO_WERKZEUGE.md) bleibt Grundlage. MicMac V1 `mm3d` stellt die benötigten Standardkommandos bereit. Eine vollständige Binärdistribution wird SolarCheck nicht beigelegt. Der Nutzer beschafft eine passende Installation separat; das ist von einer Weiterverteilung zu unterscheiden.

Der schon geprüfte [Triangle-Hinweis in v1.2.0](https://github.com/micmacIGN/micmac/blob/v1.2.0/src/geom2d/Shewchuk.README) enthält ausdrücklich: „If you are not directly supplying this code to a customer, and you are instead telling them how they can obtain it for free, then you are not required to make any arrangement with me.“ Das präzisiert die Grenze für Hinweise auf eine eigenständig beschaffte Installation. Es ist keine pauschale Freigabe aller Dateien eines MicMac-Pakets. Insbesondere die gesonderten SiftPP-Bedingungen gelten weiter; für die hier beschriebene Korrespondenzsuche sind die vorhandenen Helfer **Digeo und Ann** vorgesehen. Die konkrete Installation muss diese tatsächlich bereitstellen.

MMVII ist kein belegter Ersatz für diese V1-Kommandos: Das [aktuelle offizielle README](https://github.com/micmac-V2/MMVII/blob/a9c6ffdd16e981669e3f60492a132d9d82b87800/README.md#prerequisites) weist darauf hin, dass bestimmte Kommandos weiterhin eine MicMac-V1-Binärdatei benötigen. Ein V2-Windows-Paket allein belegt deshalb keine vollständige unabhängige Orthofotokette.

## Privater Arbeitsbereich auf dem Nutzerrechner

Originale unverändert aufbewahren. Nur bewusst erstellte Arbeitskopien verwenden, etwa getrennt in `RGB-Arbeit/` und `Thermal-Arbeit/`. MicMac schreibt Zwischenprodukte in sein Arbeitsverzeichnis; deshalb nicht im Originalordner starten. Ausgabe und Prüfprotokolle ebenfalls privat belassen. Nichts davon nach GitHub, CI, Chat oder Codex hochladen. Bekannte Bildnummern verbinden die Aufnahmen, ersetzen aber keine räumliche Sensorregistrierung.

Vor einem Lauf werden lokal festgehalten: Betriebssystem, MicMac-Version/Herkunft, tatsächlicher `mm3d`-Pfad und Verfügbarkeit der benötigten Helfer. Hier wurde lediglich festgestellt, dass `mm3d` nicht im PATH der Cloud-Umgebung liegt. Das ist keine Aussage über den Nutzerrechner.

## Standardablauf je Sensor

RGB und Thermal werden in getrennten Arbeitsverzeichnissen mit eigenen Kameramodellen verarbeitet. Die Beispiele zeigen **manuell anzupassende Upstream-Kommandos**, keinen getesteten DJI-M3T-Fertigauftrag. Aufrufpfad, Bildmuster, Auflösungen und Orientierungsnamen müssen zur lokalen Installation passen. Das Muster erfasst hier ausschließlich `.JPG`/`.jpg`-Arbeitskopien.

```text
mm3d Tapioca All ".*[.](JPG|jpg)" 1200 Detect=mm3d:Digeo Match=mm3d:Ann
mm3d Tapas RadialBasic ".*[.](JPG|jpg)" Out=Rel
```

`Tapioca`/`Tapas` übernehmen Korrespondenzen, Orientierung und Kameraparameterschätzung. Eine extern verifizierte RGB-Kalibrierungsdatei ist keine allgemeine Voraussetzung. Das passende Kameramodell und die Ergebnisqualität müssen am konkreten Bildverband geprüft werden. RGB-Parameter nicht auf Thermal übertragen.

**Vor dem nächsten Kommando:** Mit dem bestehenden MicMac-Werkzeug `OriConvert` tatsächlich vorhandene Kamerapositionen in die Orientierung `GPS` überführen. Eingabeformat, Achsen, Einheiten, horizontales CRS und Höhenbezug müssen aus der realen lokalen Quelle bekannt sein. Dafür gibt es keinen allgemeingültigen GPS-Importaufruf für sämtliche DJI-/RTK-Dateien. Das [offizielle GPS-Luftbildbeispiel](https://github.com/micmacIGN/Documentation/blob/master/DocMicMac/Generalites/QuickStartSimplified-Tools-2.tex) beschreibt `OriConvert`, `CenterBascule` und `Campari`. Seine belgische Projektion und Genauigkeitswerte sind keine Vorgaben für unseren Flug. Alternativ den dort dokumentierten Passpunktweg verwenden. Fehlende Positionen oder Referenzen nicht erfinden.

Wenn `GPS` bereits echte Positionen im gewählten metrischen Bezug enthält:

```text
mm3d CenterBascule ".*[.](JPG|jpg)" Rel GPS Ground
```

Eine zusätzliche Verfeinerung mit `Campari` richtet sich nach der tatsächlich belegten Positionsgenauigkeit; keinen festen RTK-/GPS-Genauigkeitswert für unbekannte Daten einsetzen. Vor der Orthorektifizierung Lage und Orientierung prüfen. `Ground` bezeichnet hier das Ergebnis der georeferenzierten Orientierung, keine geprüfte ebene Dachfläche.

```text
mm3d Malt Ortho ".*[.](JPG|jpg)" Ground ZoomF=2
mm3d Tawny Ortho-MEC-Malt/ RadiomEgal=0 Out=Orthophotomosaic.tif
```

`Malt Ortho` und `Tawny` erledigen Oberflächenkorrektur und Mosaik mit ihren bestehenden Algorithmen. `ZoomF=2` ist ein Beispiel, keine Qualitätszusage für Modulgrenzen. Den vollständigen Bildverband und die bekannten Problemstellen lokal prüfen. Keine eigene SolarCheck-Stitching-/SfM-Funktion als Ersatz aufrufen.

Für Thermal ist dies zunächst ein **Darstellungsweg**. `RadiomEgal=0` schaltet den radiometrischen Ausgleich aus, belegt aber weder den Erhalt numerischer Temperaturwerte noch deren Kalibrierung. Falschfarben-JPEGs und der untersuchte mittige Temperaturpunkt ergeben keine vollständige Celsiusmatrix. Ein Messwertpfad benötigt einen gesondert belegten Wertevertrag durch alle externen Stufen.

## GeoTIFF und Rückweg in SolarCheck

MicMac-TIFF plus Worldfile kann eine Lage beschreiben, ohne ein eingebettetes CRS zu enthalten. Mit dem vorhandenen freien GDAL/QGIS prüfen, ob Transform und tatsächlicher Koordinatenbezug bekannt sind. Nur dann kann beispielsweise ein GeoTIFF erzeugt werden:

```text
gdal_translate -of GTiff -a_srs "<BELEGTES_CRS>" "Ortho-MEC-Malt/Orthophotomosaic.tif" "<NEUE_AUSGABEDATEI.tif>"
```

`<BELEGTES_CRS>` und die Ausgabe sind bewusst Platzhalter. `-a_srs` weist eine bekannte Referenz zu und reprojiziert nicht. Keine unbekannte Lage durch einen EPSG-Eintrag ersetzen; ein tatsächlich passendes Worldfile/Rastertransform muss bereits vorliegen. Je Sensor eine getrennte neue Ausgabedatei anlegen, einschließlich korrekter Bandbedeutung/NoData.

In SolarCheck **Verarbeitung → „Extern erstelltes RGB-/Thermal-Paar übernehmen“** wählen. Dies öffnet den bestehenden Importbereich. Dort beide GeoTIFFs gemeinsam registrieren, anschließend **Anlagenübersicht → Orthofotos** öffnen. Paarauswahl, Überblendung und Zoom verwenden; Projekt schließen/wiederöffnen. Quellen bleiben unverändert, die Registrierung bleibt `metadata_only`. Der alte GUI-Einstieg in die eingefrorene eigene Erzeugung ist entfernt.

Die Abnahme umfasst vollständige Abdeckung, scharfe Modulränder, Doppelkonturen, Nähte und gemeinsame RGB-/Thermal-Lage. Erst ein echter lokaler Vergleich kann den fehlgeschlagenen Windows-10-Piloten ablösen. **Offen bleiben die konkrete Installation, der externe Rechenlauf und seine fachliche Abnahme.** Dieser vorbereitete Rückweg ist noch keine vollständige Umsetzung von VERT-01B.
