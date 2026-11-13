# Thermal-Orthofoto mit der vorhandenen OpenSfM-Umgebung

**THERMAL-PILOT-01 · 13.11.2026.** Ein getrenntes Thermal-GeoTIFF für das bereits erfolgreich gerechnete RGB-Projekt. Derselbe freie OpenSfM-Stand v1.1/8b6b77ef und gemeinsame Python-Kern; keine neue Installation. Der reale Thermal-Erstlauf und sein Vergleich mit RGB stehen noch aus.

**Korrektur THERMAL-MPO-FIX1:** Ein Abbruch direkt nach der Arbeitskopie bedeutet nicht, dass keine Thermaldateien importiert sind. Die ursprüngliche Prüfung akzeptierte nur den Bibliotheksnamen JPEG; gültige JPEG-Mehrbildcontainer (MPO), wie sie bei M3T vorkommen können, wurden dadurch abgewiesen. Diese Unverträglichkeit wurde mit synthetischem MPO/APP3 reproduziert. Korrigierte Prüfung akzeptiert JPEG und MPO, prüft weiterhin das vorhandene Rohdatenraster und das primäre640×512-Darstellungsbild. Kein Bildteilwechsel, keine Skalierung oder Veränderung der Quelldatei. Der ursprüngliche Screenshot allein unterscheidet die Teilursachen nicht. Bei erneutem Abbruch unterscheiden Meldung und `thermal_input_failure` jetzt Rohdaten, Bildlesbarkeit, Format und Größe.

Nach Aktualisierung denselben bereits importierten Projektbestand bewusst mit **THERMAL-Pilot starten** aufrufen. Der alte nach1s gestoppte Versuch enthält keine fortsetzbare Engineberechnung. Kein Neuimport und kein RGB-Neulauf. Der Startblock unten verweist auf die Korrekturquelle; ihr Prüfstand steht im letzten Abschnitt.

## Aktueller Schritt: gespeicherte Thermal-Teilmodelle lesen

Der Lauf vom **13.11.2026,18:58:37**, Endung **oh9ptgy5**, hat alle287 Eingaben akzeptiert. Er endete nach595,094s mit285 eindeutigen Bildern in drei Modellen; zwei fehlen. Alle fünf Engine-Stufen waren beendet, aber ein einzelner vollständiger Verbund fehlt. Darum keine Tiefenkarten/Orthofoto. Das Eingabeproblem ist geschlossen; jetzt keine unveränderte Wiederholung oder Dense-Fortsetzung starten.

1. Aktualisierten Startblock unten in PowerShell ausführen; er öffnet nur den Dialog.
2. **Lauf laden** wählen und genau den vorhandenen THERMAL-Ordner mit Start18:58:37/Endungoh9ptgy5 unter `F:\Auswertung1` auswählen. Keine Projektdateiauswahl/kein Neuimport nötig.
3. **Kennzahlen kopieren** und den Text zurückmelden. **THERMAL-Pilot starten** ist für diesen Prüfschritt nicht erforderlich.

Die neue Fassung liest nur gespeicherte `reconstruction.json` und `input-map.json`, prüft unveränderte Dateistände und passende Summen. Kein Engineaufruf, kein Matching, keine Fotos/EXIF/SQLite, keine Dateiänderung. `reconstruction_details.components` enthält Bilder/Punktdatensätze/Kameras je Modell; `pairs` enthält ausschließlich Anzahlen gemeinsamer Bild- und Punktkennungen. Namen, Pfade, Koordinaten und Kennungen werden nicht ausgegeben. Unlesbare/geänderte/widersprüchliche Dateien erhalten einen entsprechenden Status; ursprüngliche Laufkennzahlen bleiben erhalten.

**Punktzahlkorrektur:** Die erste Berichtsfassung beließ points bei mehreren Modellen auf0. Das war kein verlässlicher Nachweis leerer Teilmodelle. Die neue Ausgabe zählt `points` als Summe der Punktdatensätze je Modell (`points_scope: sum_per_model`); gemeinsame Tracks können mehrfach gezählt sein. Es ist keine Anzahl unabhängig bestätigter physischer Punkte. Die Detailzählung erteilt keine Geometrie-/Temperaturfreigabe und macht aus drei Modellen keinen vollständigen Kameraverbund.

**Geprüfte Standardwege:** OpenSfM8b6b77ef bietet merge_reconstructions für gemeinsame Track-IDs mit geometrischer Prüfung/mindestenszehn Inliern. Bloße ID-Schnittmengen reichen nicht; fehlende Bilder bleiben auch nach einem Merge offen. `reconstruct_from_prior` kopiert die Kameramodelle und Posen des Prior-Modells – das RGB-Ergebnis deshalb nicht direkt als Thermal-Kamera ausgeben. Der vorhandene Rig-Weg benötigt eigene belegte Sensorparameter, relative Sensorgeometrie und synchronisierte Zuordnung. Diese Verfahren werden hier nicht automatisch gestartet. Erst die vorhandenen Komponentenzahlen für einen gezielten nächsten Schritt verwenden, keine eigenen Pose-/Stitch-/Merge-Algorithmen oder blind erweiterten Nachtläufe.


## Thermal-Erstlauf für ein anderes Projekt starten

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

Bisherigen Pilotdialog schließen. Dieser Block lädt die feste Thermal-Fassung (ca2,9 MB) nach E:, prüft die ZIP-Prüfsumme und öffnet den Dialog. F:-Python und installierte OpenSfM-Umgebung bleiben erhalten. Keine automatische Bildverarbeitung; erst das Projekt auswählen und THERMAL-Pilot starten.

```powershell
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$pilotPython = 'F:\MCM-SolarCheck\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pilotPython -PathType Leaf)) {
    throw 'Vorhandenes SolarCheck-Python auf F: nicht gefunden.'
}
$pilotCommit = 'e7b215e0b41cb6f3282bc60cd1f5e8373a1344d5'
$pilotSha256 = 'edae7f32a97b85637595c5a5e8e6db501e19bccfb3f2ae32d279d82c7f956139'
$pilotDir = Join-Path 'E:\SolarCheck-Pilot' ('thermal-' + [guid]::NewGuid().ToString('N').Substring(0,12))
New-Item -ItemType Directory -Path $pilotDir -ErrorAction Stop | Out-Null
$pilotZip = Join-Path $pilotDir 'source.zip'
$pilotSource = Join-Path $pilotDir 'source'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pilotCommit" -OutFile $pilotZip
if ((Get-FileHash -LiteralPath $pilotZip -Algorithm SHA256).Hash -ne $pilotSha256) {
    throw 'Pruefsumme stimmt nicht. Start abgebrochen.'
}
Expand-Archive -LiteralPath $pilotZip -DestinationPath $pilotSource -ErrorAction Stop
$pilotRoot = Join-Path $pilotSource ('MCM-SolarCheck-' + $pilotCommit)
$pilotScript = Join-Path $pilotRoot 'scripts\MCM_SolarCheck_OPENSFM_THERMAL_PILOT.py'
if (-not (Test-Path -LiteralPath $pilotScript -PathType Leaf)) {
    throw 'Startdatei im entpackten Quelltext fehlt.'
}
& $pilotPython $pilotScript
if ($LASTEXITCODE -ne 0) { throw 'Pilotdialog mit Fehler beendet.' }
```


## Prüfstand der ersten Auslieferung vor MPO-Korrektur

**fdc96f06f89234896713295654453b5bacbef026:** alle drei regulären CI-Workflows grün: [Windows43459499633](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/43459499633), Linux43459488979 und43459499634, jeweils Python3.11 und3.12. Zehn tatsächliche native Tk-Fälle schließen Thermal-Start mit Erfolg/Abbruch sowie Laden→Cache→Dense-Fortsetzung→Speichern→Wiederladen→Kopieren ein. Synthetische Fälle prüfen APP3-/Mittelpunkt-Rohwerterhalt, unveränderte Originale, read-only Projektwahl, falsche/gemischte Modalitäten, fehlende/falsche Sensorgeometrie, Teilmodelle, Zeitlimit und sensorgetrennte Fortsetzung. Erste3.11-Syntaxfehler in Status-/Fehleranzeigen wurden vor dieser Auslieferung korrigiert; alle gelieferten Laufzeitdateien werden mit dem jeweiligen Testinterpreter kompiliert.

Lokaler letzter gezielter Lauf27Tests grün; zuvor106Tests/zehn Tk-Skips unter Linux. Die feste Quell-ZIP (2921780Bytes) und neun ausgelieferte Codeeinträge wurden bytegenau gegen diesen Commit geprüft; SHA256 steht im Startblock. Nachfolgenden reinen Dokumentations-HEAD separat prüfen. Windows-Server-CI und synthetische Engine-Ergebnisse sind kein realer Windows10-Thermal-/Geometrie-/Temperaturnachweis; der lokale Thermal-Erstlauf bleibt offen. Keine Originalbilder, produktiven Datenbanken oder Kundendaten hier verarbeitet. Draft PR9 bleibt offen, kein Merge nach main.


## Prüfstand der MPO-Korrektur

Quelle **8b6165b4670b157fd5189f05b1743727ff8a07c7**: JPEG/MPO-Freigabe mit unverändertem Rohdatenparser, primärem640×512-Bild und getrennten Fehlergründen. Lokal67 gezielte Tests grün/zehn Tk-Skips, zwei Übergabeprüfungen grün. Synthetischer MPO-Vollpfad einschließlich OpenCV-Primärbildvergleich und unveränderter Quell-/Arbeitskopien; Negativfälle Rohdaten/Lesbarkeit/Format/primäre Dimension. Keine private Originaldatei hier geöffnet. Alle drei regulären CI grün: [Windows43471400588](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/43471400588) auf Python3.11/3.12 einschließlich MPO-Fall und nativer Tk-Bedienung, Linux43471400580 und43471391534 auf3.11/3.12. Nachfolgenden reinen Dokumentations-HEAD separat prüfen.

Feste Quell-ZIP2924724Bytes, neun Codeeinträge bytegenau gegen diese Quelle geprüft; SHA256 im Startblock. Die konkrete Teilursache des ursprünglichen Nutzerbildes war im alten Sammelfehler nicht erkennbar. Die MPO-Fehlablehnung ist reproduziert/korrigiert, realer Wiederholungsbefund noch offen. Bei fortbestehendem Abbruch nur **Kennzahlen kopieren**; `thermal_input_failure` benennt den Teilcheck ohne private Pfade oder Rohwerte. Keine automatische Aufweichung des Rohdaten-/Geometrienachweises, keine neue Installation.


## Prüfstand COMPONENT-READ-01

Lokal74 gezielte Tests bestanden/elf native Tk-Fälle ohne Display übersprungen. Neue Fälle: Mehrmodell-Punktsumme, Legacy0-Korrektur nur in der Anzeige, überlappende Modelle ohne doppelte Bildzählung, ausschließlich numerische Schnittmengen, keine Berechnung/Schreibzugriffe, unlesbare/veränderte/falsche Zuordnung/Verknüpfung abweisen. Zusätzlicher nativer Tk-Fall lädt einen gescheiterten Thermal-Verbund, kopiert korrekte Summen und lässt Cache-/Dense-Knöpfe gesperrt. Quelle **e7b215e0b41cb6f3282bc60cd1f5e8373a1344d5**: alle drei regulären CI grün, [Windows43482072665](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/43482072665) auf Python3.11/3.12 einschließlich tatsächlicher Thermal-Lade-/Kopierbedienung, Linux43482071961/43482062215. Feste Quell-ZIP2930907Bytes/SHA256 im Startblock; neun Codeeinträge bytegenau geprüft. Nachfolgenden reinen Dokumentations-HEAD separat prüfen. Keine Originalbilder oder produktiven Daten hier verarbeitet.
