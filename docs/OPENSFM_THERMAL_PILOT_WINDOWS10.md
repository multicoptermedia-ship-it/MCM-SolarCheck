# Thermal-Orthofoto mit der vorhandenen OpenSfM-Umgebung

**THERMAL-PILOT-01 · 13.11.2026.** Ein getrenntes Thermal-GeoTIFF für das bereits erfolgreich gerechnete RGB-Projekt. Derselbe freie OpenSfM-Stand v1.1/8b6b77ef und gemeinsame Python-Kern; keine neue Installation. Der reale Thermal-Erstlauf und sein Vergleich mit RGB stehen noch aus.

## Thermal starten

1. Den unten stehenden Startblock vollständig in **PowerShell** einfügen. Er lädt ausschließlich SolarCheck-Quellcode, prüft dessen SHA256 und öffnet den neuen **THERMAL-Dialog** mit dem bisherigen F:-Python. Fotos werden erst nach dem Startklick lokal verarbeitet.
2. Die bisherige **Projektdatei** und dasselbe Projekt wie beim erfolgreichen RGB-Lauf wählen. Die installierte Conda-Datei und `E:\SolarCheck-OpenSfM\env` bleiben vorbelegt. Als privaten Ausgabeordner wieder beispielsweise `F:\Auswertung1` wählen.
3. **THERMAL-Pilot starten** anklicken. Verarbeitet werden nur die bereits importierten M3T-Thermal-JPGs, **keine RGB-Bilder**. Keine Bilder erneut importieren; das fertige RGB-Orthofoto bleibt erhalten.
4. Nach Abschluss **Ausgabeordner oeffnen**. Die Ausgabe liegt im neuen Ordner `JJJJMMTT_HHMMSS_OpenSfM_THERMAL_Projekt_…`, darin **`undistorted\depthmaps\ortho.tif`**. Der eigene Ordner unterscheidet sie vom gleichnamigen RGB-Ergebnis. Lokal in IrfanView die PV-Flächen auf Lücken, Doppelkonturen und versetzte Teile prüfen.
5. **Kennzahlen kopieren** und die Summen als Text zurückmelden. Originale, Rohprotokolle, GPS/EXIF und private Raster bleiben lokal. **Lauf laden** öffnet später denselben Thermal-Ordner ohne neue Berechnung; ein RGB-/COLMAP-Lauf wird im Thermal-Dialog abgewiesen.

Zeitgrenzen: maximal60 Minuten je erster Stufe, drei Stunden insgesamt. Bei einem Tiefenkarten-Zeitlimit den vorhandenen Thermal-Lauf laden, **Tiefenkarten pruefen → Tiefenkarten fortsetzen** verwenden. Die Fortsetzung nutzt dieselbe geprüfte Speicher-/Prozess-/Cachelogik wie RGB, nur die drei Dense-Stufen, maximalzwei Stunden für Tiefenkarten/drei Stunden insgesamt. Keine automatische Wiederholung oder Cachelöschung. Bei fehlendem vollständigen Thermal-Kameraverbund wird vor der dichteren Berechnung gestoppt.

## Was erhalten bleibt und was ausgegeben wird

Die schon importierten Datensätze werden nur lesend über denselben SQLite-Adapter geladen, ausdrücklich aus `thermal_frames`. Originaldateien bleiben unverändert. Die privaten JPEG-Kopien behalten **sämtliche Bytes einschließlich APP3/4/5**. Der vorhandene M3T-Parser prüft auf diesen Kopien das640×512-16-Bit-Raster; eine SHA256-Prüfung nach dem Lauf bestätigt den unveränderten Kopieninhalt. Das erhält auch die Daten zum früher untersuchten mittigen Messpunkt; dieser Pilot liest oder erfindet dafür keinen Celsiuswert. [Vorhandene Nachweise und offene Temperaturumrechnung](THERMAL_PRUEFSTAND_2026-11-13.md).

OpenSfM rechnet auf dem dargestellten Thermal-JPEG mit **eigenen Thermal-Metadaten und Kameramodellen**, ohne RGB-Kalibrierung, RGB-Rekonstruktion oder Kameraüberschreibungsdatei. Unbekannte Brennweite oder unpassende Sensordimensionen werden nicht geraten. Dieselben zehn Standardstufen wie beim RGB-Weg; keine selbst entwickelte Photogrammetrie und keine ODM-Anbindung.

Das erzeugte GeoTIFF ist eine **Thermal-Darstellung** (`thermal_value_kind: visual`). Die Bildzusammensetzung/Überblendung ist **kein radiometrisches16-Bit- oder Celsius-Orthofoto**. Für spätere Temperatur-/Rohwertanalyse bleiben die Originalraster und ihre Quellenzuordnung erhalten. `radiometric_sources_preserved` zählt die geprüften Kopien; es bestätigt keine Temperaturkennlinie oder radiometrische Erhaltung im Mosaik. `thermal_created` bedeutet hier nur Darstellungsartefakt erstellt. `temperature_matrix_created`, `temperature_verified` und `georeferencing_verified` bleiben **false**.

## Danach: vorhandenes RGB-/Thermal-Paar prüfen

Erst das reale Thermal-Ergebnis ansehen. Danach das erhaltene RGB-GeoTIFF und dieses Thermal-GeoTIFF über **Verarbeitung → Extern erstelltes RGB-/Thermal-Paar übernehmen** in den bestehenden Paarimport geben. Die vorhandene GIS-/GeoTIFF-Prüfung, atomare Registrierung und Anlagenübersicht mit Überblendung weiterverwenden. Verschiedene Pixelgrößen sind möglich; CRS, Lage und reale PV-Überdeckung müssen zusammenpassen. GPS-Header allein oder eine saubere Ansicht des einzelnen Rasters belegen noch keine genaue Sensorüberlagerung. Dieser Pilot schreibt deshalb nicht automatisch in die Projektdatei.

Wenn beide Bilder räumlich passen, folgt der vorhandene PV-/Rohwert-Vorschlags-/Review-Weg. Falschfarben im Mosaik nicht in Temperaturen umdeuten. Dachauswahl/FDach-Qualifikation bleibt der anschließende getrennte Schritt.

## Aktualisierter Startblock

Der feste Download-/Startblock wird nach erfolgreicher Prüfung dieser Quellfassung ergänzt. Alte RGB-Startblöcke starten weiterhin den RGB-Dialog; damit das RGB-Projekt nicht neu rechnen.
