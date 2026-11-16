# Thermal-Orthofoto mit der vorhandenen OpenSfM-Umgebung

## PV-Modul-Entwürfe im gespeicherten Vergleich16.11.2026

Der lokale visuelle RGB-/Thermal-Vergleich, Speicherung und Wiederöffnung sind laut Nutzer bestätigt. Mit der **aktualisierten festen Startfassung** den bisherigen fertigen Thermal-Lauf laden → **RGB vergleichen**. Der gespeicherte Vergleich wird wieder geöffnet; keine Neuberechnung/kein neuer Bildabgleich. **PV-Modulgrenzen und Entwurfs-IDs prüfen** öffnet die bestehende Ausschnitt-/Detektorprüfung. Der Knopf wird erst nach lokal als passend gespeichertem Sichtvergleich aktiv.

1. Im RGB mit der Maus einen begrenzten Bereich mit mehreren erkennbaren Modulen markieren(maximal2048×2048Originalpixel). **PV-Modulvorschläge suchen** nutzt den vorhandenen konservativen OpenCV-Detektor ohne neue Modelle/Downloads oder Schwellenschleifen.0Treffer sind möglich; eine vollständige Anlage wird nicht automatisch erkannt/freigegeben.
2. Umrisse und Entwurfs-IDs(z.B. **A1:M-0001**) in Bild und Tabelle vergleichen. IDs gelten nur in diesem gespeicherten RGB-Ausschnitt; keine bestätigten physischen Modul-IDs oder automatische Zusammenführung überlappender Ausschnitte. Pro Zeile **offen / Umriss passt / verwerfen** wählen und optional lokale Notiz(max1000Zeichen) eintragen. Die Umrisse werden dadurch nicht automatisch korrigiert; falsche Vorschläge verwerfen.
3. Zeile auswählen → **Ausgewähltes Modul in RGB / Thermal vergleichen**. Das Modulfenster benutzt dieselben gespeicherten GeoTIFF-Koordinaten und die vorhandene Überblendung; keine geschätzte Lagekorrektur oder Temperaturauswertung. Der Anteil gültiger Thermalpixel bezieht sich nur auf das Modulpolygon und ist keine Bestätigung vollständiger Anlagenabdeckung. Fehlende Thermalbereiche bleiben fehlend und lassen RGB sichtbar.
4. **Modul-Entwürfe und Prüfung lokal speichern**, schließen und über denselben Knopf erneut öffnen. Gespeicherte Ausschnitte, IDs, Umrissstatus und Notizen werden ohne erneute Detektion geladen. Oben zwischen gespeicherten Ausschnitten wechseln oder neuen RGB-Bereich markieren. Maximal20Ausschnitte/2000Entwürfe; gespeicherte IDs nicht durch automatische Neusuche umnummerieren. Schließen ohne Speichern übernimmt keine Änderungen.

`pv-modules.LOCAL.json` bleibt im privaten Vorschauordner. Enthält Dateiprüfsummen, native Polygonkoordinaten, lokale Entwurfs-IDs und Notizen; **nicht hochladen/ins Repository kopieren**. Diese Angaben erscheinen nicht in teilbaren Kennzahlen. Geänderte Quelldateien oder beschädigte IDs/Polygone/Freigaben stoppen die Wiederöffnung/Speicherung.

Dauerlabel **unvollständig: 280 von 287 Bildern**, reguläre Paarimport-Sperre und alle Freigabeflags bleiben erhalten. Weder „Umriss passt“ noch der gespeicherte Lage-Sichtbefund bestätigt physische Modulidentität, geometrische Genauigkeit, vollständige Flächenabdeckung oder Celsiuswerte. Keine produktive DB-/Berichtsfreigabe; zuerst diesen lokalen Nutzerweg qualifizieren.


## RGB-Sichtvergleich16.11.2026: unvollständige Vorschau erhalten

Nutzer bestätigt die erste Thermal-Übersicht als gut. Im **aktualisierten Thermal-Dialog** den vorhandenen fertigen Lauf laden → **RGB vergleichen** → fertiges RGB-GeoTIFF desselben Projekts bewusst auswählen. Keine Originalbilder/Projektdatei neu importieren. Der Vergleich öffnet sich mit vorhandenem SolarCheck-Python in eigenem Fenster, ohne OpenSfM-Start oder Paarregistrierung.

Das bestehende Überblendungswidget startet mit50%Thermal; per Schieber zwischen RGB/Thermal wechseln und gemeinsam zoomen/scrollen. Grundlage sind die gespeicherten GeoTIFF-Koordinaten, keine automatische Verschiebungs-/Kamerakorrektur. Fehlende Thermalpixel zeigen RGB. Begrenzte Übersicht(max2048Kantenpixel); „100%“ bedeutet Vorschaugröße, Details in Original-TIFFs prüfen. Dauerlabel **unvollständig: 280 von 287 Bildern** bleibt sichtbar; keine Bestätigung von Abdeckung, Geometriequalität oder Celsius.

Modul-/Dachkanten und Aufbauten in Mitte/Randbereichen vergleichen. „In dieser Ansicht passend“ oder „Versatz sichtbar“ als lokalen Sichtbefund wählen, optional Notiz(max2000Zeichen). **Sichtvergleich lokal speichern** speichert Auswahl/Notiz, Deckkraft/Zoom und Prüfsummen in `rgb-comparison.LOCAL.json` im privaten Vorschauordner. Beim nächsten **RGB vergleichen** werden die Angaben geladen. **Anderes RGB wählen** erlaubt eine bewusste neue Auswahl. Schließen ohne Speichern oder Dateidialog-Abbruch übernehmen nichts; geänderte Dateien müssen erneut bewusst gewählt werden. Raster/Geotags bleiben unverändert. Private Dateien/Notizen nicht hochladen; sie erscheinen nicht in „Kennzahlen kopieren“.

Regulärer RGB-/Thermal-Paarimport bleibt gesperrt. Keine neue Matching-/SfM-/Dense-Rechnung oder vollständige Fachfreigabe. Reale Überdeckung und geometrische Genauigkeit bleiben noch nachzuweisen.


## Lokaler Abschluss16.11.2026: Teilvorschau fertig, Sichtprüfung offen

Der Nutzerbericht bestätigt `incomplete_thermal_preview.status: finished`: **unvollständig: 280 von 287 Bildern**, sieben ausgeschlossen, alle fünf Vorschau-Stufen fertig. Das obere `failed`,595,094s sowie0raw/0clean gehören zur ursprünglichen Kameralaufhistorie; sie beschreiben weder Erfolg noch Laufzeit der Teilvorschau. `thermal_created: false` und `orthophoto_created: false` bleiben beabsichtigt, weil kein vollständiges freigegebenes Ergebnis vorliegt.

Jetzt **Ausgabeordner oeffnen** und die bereits erzeugte `undistorted/depthmaps/UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif` ausschließlich lokal betrachten, gegebenenfalls im vorhandenen QGIS neben dem fertigen RGB. Modulränder, Doppelkonturen, Nähte, Löcher und Lage zum RGB prüfen und den Befund nur als Text mitteilen. Die Bilddatei und `excluded-images.LOCAL.json` bleiben lokal. Keine Neuberechnung, keine Fortsetzung eines bereits fertigen Vorschauversuchs, kein weiterer Matchinglauf/Neuimport. Der reguläre Paarimport bleibt gesperrt. Bildqualität, Flächenabdeckung, unabhängige Geometrie und Celsiuswerte sind noch nicht bestätigt.


## Aktuell16.11.2026: ausdrücklich unvollständige Thermal-Teilvorschau

RGB ist lokal erfolgreich geprüft; nicht neu rechnen. Thermal: Hauptmodell280 von287 Bildern, Zusatzabgleich ausgeschöpft. **Keine neuen Matchingläufe.** Ältere Zusatzabgleich-/Erstlaufanweisungen unten sind Historie; der aktualisierte Startblock öffnet die neue Teilvorschaufassung.

Den aktualisierten Startblock unten verwenden (feste Quellfassung4c876a10, ZIP-SHA256 und25Laufzeitdateien bytegenau geprüft; bestehender ZIP-/F:-Python-Start bleibt erhalten). Im Thermal-Dialog **Lauf laden** und den vorhandenen gescheiterten Thermal-Lauf mit dem280er Hauptmodell auswählen. Keine Projektdatei/Originalbilder neu importieren. **Unvollstaendige Thermal-Teilvorschau** anklicken; bewusst gestartete lokale Verarbeitung, maximal60Minuten je Stufe/drei Stunden insgesamt. Es laufen nur native Entzerrung, Cluster, Tiefenkarten, Fusion und GeoTIFF aus den bestehenden eigenen Thermalposen. Kein Matching, keine Kamerarekonstruktion, kein RGB-Neulauf.

**Ausgabeordner oeffnen** führt zum getrennten `thermal-partial-*`-Ordner. Dort liegen `partial-preview.json` und nach Erfolg `undistorted/depthmaps/UNVOLLSTAENDIG_THERMAL_TEILVORSCHAU.tif` samt Warntext. GeoTIFF-Tags und Dialog tragen dauerhaft „unvollständig: 280 von 287 Bildern“ (tatsächliche Zahlen aus gespeichertem Hauptmodell). `excluded-images.LOCAL.json` ordnet die sieben ausgeschlossenen Bilder ihren gespeicherten Arbeits-/Quellkennungen zu; ausschließlich lokal öffnen, nicht kopieren/hochladen. Quellen und gespeicherte Thermalposen bleiben unverändert; Sperre/Verweis liegen neben dem Quelllauf. Bericht und Dialog nennen einbezogene/ausgeschlossene Bilder.280/287 Bilder sind keine gemessene Flächenabdeckung. Ausgangslauf erneut laden zeigt gespeicherten Vorschauzustand, der Vorschauknopf öffnet den vorhandenen Stand ohne Neuberechnung. Abbrechen beendet den eigenen Prozessbaum; Fehler/Timeout bleiben gespeichert. Nach Abbruch/Timeout den Ausgangslauf laden → **Teilvorschau fortsetzen**: Quell-/Arbeitskopieprüfsummen und eigene Thermalgeometrie prüfen, dann ab der ersten nicht abgeschlossenen Stufe fortsetzen; bereits abgeschlossene Stufen erhalten. Unvollständige Vorbereitung kann nicht fortgesetzt werden. Kein automatischer Wiederholungsversuch.

Nur Darstellung zur lokalen Sichtprüfung. Fehlende Bereiche, Nähte, Doppelkonturen, Modulränder und Lage zum fertigen RGB prüfen. **Keine vollständige Qualitäts-, Geometrie-, Temperatur- oder Celsiusfreigabe, kein fertiges vollständiges Thermal-Orthofoto.** Der reguläre RGB-/Thermal-Paarimport ist für diese Vorschau gesperrt, auch nach Umbenennen oder Kopieren dank GeoTIFF-Metadaten. Kundenbilder und Raster bleiben lokal, nur Quellcode und synthetische Tests in Git/CI.


**THERMAL-PILOT-01 · 13.11.2026.** Ein getrenntes Thermal-GeoTIFF für das bereits erfolgreich gerechnete RGB-Projekt. Derselbe freie OpenSfM-Stand v1.1/8b6b77ef und gemeinsame Python-Kern; keine neue Installation. Der reale Thermal-Erstlauf und sein Vergleich mit RGB stehen noch aus.

**Korrektur THERMAL-MPO-FIX1:** Ein Abbruch direkt nach der Arbeitskopie bedeutet nicht, dass keine Thermaldateien importiert sind. Die ursprüngliche Prüfung akzeptierte nur den Bibliotheksnamen JPEG; gültige JPEG-Mehrbildcontainer (MPO), wie sie bei M3T vorkommen können, wurden dadurch abgewiesen. Diese Unverträglichkeit wurde mit synthetischem MPO/APP3 reproduziert. Korrigierte Prüfung akzeptiert JPEG und MPO, prüft weiterhin das vorhandene Rohdatenraster und das primäre640×512-Darstellungsbild. Kein Bildteilwechsel, keine Skalierung oder Veränderung der Quelldatei. Der ursprüngliche Screenshot allein unterscheidet die Teilursachen nicht. Bei erneutem Abbruch unterscheiden Meldung und `thermal_input_failure` jetzt Rohdaten, Bildlesbarkeit, Format und Größe.

Nach Aktualisierung denselben bereits importierten Projektbestand bewusst mit **THERMAL-Pilot starten** aufrufen. Der alte nach1s gestoppte Versuch enthält keine fortsetzbare Engineberechnung. Kein Neuimport und kein RGB-Neulauf. Der Startblock unten verweist auf die Korrekturquelle; ihr Prüfstand steht im letzten Abschnitt.

## Historie13.11.2026: sieben Außenbilder gezielt abgleichen (ausgeschöpft)

Die gespeicherte Prüfung ist abgeschlossen:280Bilder bilden das Hauptmodell,3 und2 liegen in kleinen Modellen, zwei fehlen. Die5 gemeinsamen Punktkennungen0↔1 reichen nicht für den Standardmerge; zu Modell2 fehlen gemeinsame Punkte vollständig. Kein erneuter unveränderter Komplettlauf.

1. Alten Dialog schließen und den aktualisierten Startblock unten in PowerShell ausführen.
2. **Lauf laden** → den vorhandenen Thermal-Lauf vom **13.11.2026,18:58:37**, Endung **oh9ptgy5**, auswählen.
3. **Zusatzabgleich starten** anklicken. Projekt-/Datenbankwahl und Neuimport sind dafür nicht nötig.
4. Der Dialog wechselt auf einen neuen Lauf unter einem eigenen **sparse-bridge-…**-Ordner neben dem alten Lauf. Dessen neue Kennzahlen anschließend kopieren; bei Erfolg `undistorted\depthmaps\ortho.tif` lokal sichten.

Der einmalige Versuch übernimmt die vorhandenen privaten Arbeitskopien, gespeicherte Metadaten, Merkmale und Matches bytegeprüft in einen separaten Ordner. Die Originale und bisherigen Ergebnisse bleiben erhalten. Neue Lock-/Versuchsmarker liegen im Quellordner; sie verhindern Parallelstart und wiederholte Versuche. Ein abgebrochener/fruchtloser Versuch wird nicht automatisch wiederholt. Bei Fehler neue Kennzahlen kopieren, keine Marker/Caches löschen.

Nur die sieben Bilder außerhalb des Hauptmodells werden OpenSfM als Referenzmenge übergeben. Die native Paarauswahl betrachtet deren Kombinationen mit allen Bildern: maximal1981 eindeutige Paare, inklusive Außenbilder untereinander. Bereits gespeicherte Paarergebnisse beider Richtungen, auch erfolglose/leere, werden übersprungen und nicht überschrieben. Descriptoren, Kameramodelle und Matching-Schwellen bleiben unverändert. Native DataSet-Lader lesen die gespeicherten Feature-/Matchformate; kein eigener Deskriptorvergleich/RANSAC/SfM oder direkter unsicherer Pickle-Lader.

Metadaten und Merkmale werden nicht neu berechnet. Nach dem Zusatzabgleich erzeugt OpenSfM neue Tracks und eine neue Kamerarekonstruktion. Ohne neue robuste Paarverbindungen stoppt der Versuch sofort. Nur bei genau einem vollständigen endlichen287er Kameraverbund mit eigener Thermalgeometrie läuft die bisherige Standard-Dense-/GeoTIFF-Kette weiter. Eine280er Teilgruppe gilt nicht als fertiges Gesamtergebnis. Es werden keine RGB-Posen/-Intrinsics übertragen und keine Bilder nach GPS zwangsplatziert.

Zeitgrenzen bleiben maximal60Minuten pro Stufe und drei Stunden insgesamt, einschließlich Kopien und weiterer Standardstufen. **Abbrechen/Schließen** beendet den eigenen Prozessbaum; Dateien bleiben zur Prüfung erhalten. Das neue GeoTIFF ist weiterhin eine Darstellung, keine Celsiusmatrix/Geometriefreigabe. Bei einem späteren Dense-Zeitlimit kann der **neue vollständige** Lauf über den vorhandenen Cache-/Fortsetzungsweg weiterverwendet werden; der alte Teilmodell-Lauf bleibt dafür ungeeignet.

## Abgeschlossene Vorprüfung: gespeicherte Teilmodelle lesen

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

Bisherigen Pilotdialog schließen. Dieser Block lädt ausschließlich die feste SolarCheck-Quellfassung4c876a10 (2991598Bytes) nach E:, prüft die ZIP-Prüfsumme und öffnet den Thermal-Dialog mit vorhandenem F:-Python. Danach **Lauf laden → RGB vergleichen → PV-Modulgrenzen und Entwurfs-IDs prüfen** (vorhandene fertige Teilvorschau und gespeicherter Vergleich), keinen neuen THERMAL-Piloten oder Zusatzabgleich starten. Bestehende OpenSfM-Umgebung bleibt erhalten. QuellZIP/25Laufzeitdateien bytegenau geprüft; exakte CI dieses Codes noch separat prüfen.

```powershell
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$pilotPython = 'F:\MCM-SolarCheck\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pilotPython -PathType Leaf)) {
    throw 'Vorhandenes SolarCheck-Python auf F: nicht gefunden.'
}
$pilotCommit = '4c876a107c91d874ffeb4efb030a7ff29c272cfc'
$pilotSha256 = 'ae878f79cfce8d64a95782bc871a3d105737cc3fa1b645bb9061fbc7e61b59e6'
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


## Prüfstand des gezielten Zusatzabgleichs

Lokal81Tests grün/13native Tk-Fälle ohne Display übersprungen. Neue Fälle prüfen Cache-/Rohdatenbyteerhalt ohne erneuten Decoder, nur Zusatzmatching/Tracks/Reconstruct statt erster zwei Stufen, volle Geometrieprüfung vor Dense, Timeout/fehlende neue Links/Teilmodelle/Quelländerung/Prüfsummenfehler, Einmalmarker und negative Voraussetzungen. Isolierter 64-Bit-Prozess prüft Übergabe an native API mit nur Außenbildern, Erhaltung alter Matches beider Richtungen/auch leerer und korrekten Counts. Native Tk-Fälle für Start/Wechsel zum neuen Job/Kennzahlen/Erfolg und Abbruch bestanden. Quelle **29eb9c99f07657a2e0b29d2cb729e7e419004d71**: alle drei regulären CI grün, [Windows43486193637](https://github.com/multicoptermedia-ship-it/MCM-SolarCheck/actions/runs/43486193637) auf Python3.11/3.12 inklusive tatsächlicher Bedienung und isolierter nativer API-Grenze, Linux43486193621/43486185568. Feste Quell-ZIP2943112Bytes/SHA256 im Startblock, zehn Codeeinträge bytegenau geprüft. Nachfolgenden reinen Dokumentations-HEAD separat prüfen; keine privaten Bilder hier verarbeitet.
