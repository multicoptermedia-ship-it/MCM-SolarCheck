# Vorhandene Versuchsgewichte auf einzelne Modulvorschläge prüfen

Stand26.11.2026 · PVIS-INSTANCE-VALIDATION-01 · [aktueller Entwicklungsstand](AKTUELLER_ENTWICKLUNGSSTAND.md).

Dein Trainingslauf und der erneut geöffnete Bericht sind technisch bestanden: drei Epochen/24Schritte/59veränderte Parametertensoren, Run473cb989…41ec2, Berichts-SHAc3c0bbae…87a7c und Gewichts-SHAcf56d5d4…caff identisch. **Training nicht wiederholen.** Die Flächen-IoU fiel von24,45auf20,54Prozent; bisher keine bessere Modulerkennung belegt.

Dieser neue Schritt liest dieselben gespeicherten Versuchsgewichte und die acht bereits gespeicherten Validierungsausschnitte aus Anlage033. Er erzeugt einzelne Kandidatenmasken, zählt sie und vergleicht sie mit den veröffentlichten Instanzmasken. **Keine Trainingsrunde, Installation oder neuen Bilder-/Modelldownloads.** Prüfanlage024 wird nicht als Bild geöffnet. Kundendaten und bisherige Modelle bleiben erhalten. Die drei ursprünglichen Trainings-/Ladedateien sowie deren Modellfabrik sind gegenüber der Trainingsquelle825cd57d unverändert; der vorhandene Lauf wird weiterverwendet.

Bitte den folgenden Instanzprüfstart verwenden; nicht erneut den bisherigen KI-Modellvergleich im privaten PV-Ausschnitt ausführen.

## Start

Den vollständigen Block in PowerShell ausführen. Er lädt nur die geprüfte SolarCheck-QuellZIP in einen eigenen Startordner und verwendet dein vorhandenes F:-App-Python sowie E:-Torch-Python:

```powershell
$ErrorActionPreference = 'Stop'
$pvInstanceCommit = 'SOURCE_COMMIT'
$pvInstanceStart = Join-Path 'E:\SolarCheck-PVIS-Instanzpruefung-Start' $pvInstanceCommit
New-Item -ItemType Directory -Force -Path $pvInstanceStart | Out-Null
$pvInstanceZip = Join-Path $pvInstanceStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvInstanceCommit" -OutFile $pvInstanceZip
if ((Get-FileHash -Algorithm SHA256 $pvInstanceZip).Hash.ToLowerInvariant() -ne 'SOURCE_SHA256') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvInstanceZip -DestinationPath $pvInstanceStart -Force
$pvInstanceSource = Join-Path $pvInstanceStart "MCM-SolarCheck-$pvInstanceCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pvInstanceSource 'scripts\MCM_SolarCheck_PVIS_INSTANZPRUEFUNG.py') --validate-instances --prefix 'E:\SolarCheck-PVIS-Training' --torch-prefix 'E:\SolarCheck-CVUT-KI-Pilot'
if ($LASTEXITCODE -eq 0) {
    $pvInstanceReport = Get-Content -LiteralPath 'E:\SolarCheck-PVIS-Training\instance-validation.json' -Raw -Encoding UTF8 | ConvertFrom-Json
    $pvInstanceFolder = Join-Path 'E:\SolarCheck-PVIS-Training\instance-validation' $pvInstanceReport.evaluation_id
    $pvInstancePreview = Get-ChildItem -LiteralPath $pvInstanceFolder -Filter '*-preview.png' | Sort-Object Name | Select-Object -First 1
    if ($null -ne $pvInstancePreview) { Invoke-Item -LiteralPath $pvInstancePreview.FullName }
} else {
    Write-Host 'Bitte nur den JSON-Diagnoseblock mitteilen. Kein Training und kein Setup wiederholen.'
}
```

Feste Quelle SOURCE_COMMIT, ZIP SOURCE_BYTES Bytes, SHA256 SOURCE_SHA256. Laufzeitquellen und Konfiguration werden gegen das remote geladene Archiv geprüft; exakte finale HEAD-CI in Draft PR9.

In PowerShell erscheinen acht Fortschrittszeilen **Instanzpruefung Validierung** und ein JSON-Bericht. Es erscheinen keine neuen Trainingsepochen. Anschließend öffnet der vorhandene Bildbetrachter das erste öffentliche Kontrollbild. Weitere Kontrollbilder liegen im gleichen Auswertungsordner. Rund20MB freier Platz reichen für diese begrenzten Diagnoseartefakte.

Jedes Kontrollbild zeigt vier Spalten: RGB/256, veröffentlichte Referenz mit Magenta für ignorierte Pixel, unabhängig erzeugte Versuchsvorschläge und eine graue PV-Wahrscheinlichkeitskarte. Weißer in der letzten Spalte bedeutet höhere Modellwahrscheinlichkeit, keine Temperatur. Gelbe Konturen sind tatsächliche Maskengrenzen; daraus keine geprüften vier Modulecken, geometrische Genauigkeit oder physischen Modul-IDs ableiten.

## Bericht richtig lesen

- validation_crops: acht ausgewählte Validierungscrops, keine vollständigen Bilder oder Anlage.
- scored_crops und unscored_crops: vollständig ausgewertete und ausdrücklich unbewertete Ausschnitte. all_validation_crops_scored=false ist bei Abbrüchen der Segmentierung eine wichtige Einschränkung.
- reference_instance_observations_all_crops: Referenzbeobachtungen aller acht Crops; keine eindeutigen physischen Module des Parks.
- candidate_instances_complete_crops: Kandidaten nur aus vollständig segmentierten Crops. partial_diagnostic_regions_unscored_crops enthält lediglich vorläufige Regionen aus unbewerteten Crops; diese sind keine bestätigte Modulzahl und gehen nicht in Precision/Recall ein.
- metrics.reference_instances, scored_prediction_instances, matched_instances, missed_references und additional_predictions beziehen sich **nur auf scored_crops**. Gleiche Anzahl bei falschen Umrissen ist kein Treffer. Masken-IoU mindestens0,5 und eindeutige Zuordnung; weder Referenz noch Kandidat mehrfach als Treffer zählen.
- precision, recall und f1 gelten nur gegenüber diesen veröffentlichten projizierten Referenzmasken. Keine allgemeine Trefferquote, mAP, vollständige Abdeckung oder Produktfreigabe. precision=null bei null bewerteten Vorschlägen ist undefiniert, nicht100Prozent. Bei ausschließlich unbewerteten Crops bleibt metrics=null.
- inference_images_by_split zeigt0Training/8Validierung/0Test. Das Zahlenpaket enthält weiterhin16vorhandene öffentliche Crops; nur die acht033-Crops erhalten neue Modellvorhersagen. Keine Original-JPEGs neu dekodieren.
- training_started=false, model_updated=false und instance_detection_ready=false bleiben beabsichtigt: Vorhersage/Decoder laufen, Erkennungsqualität und Kundenvergleich sind noch nicht qualifiziert. Der Bericht ist kein neues Modellmanifest.

Die zusätzliche öffentliche Linux-Probe mit unveränderten Gewichten hat **noch keine brauchbare Modultrennung** ergeben:8Crops/36Referenzbeobachtungen, davon3vollständig auswertbar mit15Referenzen und5Kandidaten,0Treffer/15fehlend/5zusätzlich;5Crops wegen Regions-/Kandidatengrenze unbewertet.171dort vorläufig gefundene Regionen werden separat geführt und nicht als gültige Modulzahl behandelt. Instanz-Precision/Recall/F1 der drei bewerteten Crops jeweils0. Die dortige Flächen-IoU0,3267 ist wegen der anderen Teilmenge **nicht mit der bisherigen Acht-Crop-IoU0,2054 als Verbesserung vergleichbar**. Dies ist ein diagnostischer Befund, kein Modellfortschritt. Kleine numerische Windows-/Linux-Unterschiede nahe dem Schwellenwert können die Segmentierung verändern; identische Zahlen über Betriebssysteme werden nicht vorausgesetzt.

## Speichern und Wiederöffnung

Nach Schließen und erneutem Öffnen von PowerShell diesen vollständigen Befehl ausführen:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Instanzpruefung-Start\SOURCE_COMMIT\MCM-SolarCheck-SOURCE_COMMIT\scripts\MCM_SolarCheck_PVIS_INSTANZPRUEFUNG.py' --prefix 'E:\SolarCheck-PVIS-Training' --show
```

--show prüft Parent-Lauf, Zahlenpaket, Gewichte, gespeicherte Masken und Kontrollbilder, rechnet Maskenzuordnung/Kennzahlen erneut aus den gespeicherten Rastern und vergleicht den Abschlussbericht. **Keine Torch-Modellinstanz, Inferenz, Trainingsrunde oder Original-JPEG-Dekodierung.** Derselbe Bericht muss wieder erscheinen. Bitte nur den JSON-Text mitteilen, keine Bilder oder Gewichte hochladen.

Originaler report.json/latest.json, Versuchsgewichte, Referenzarchive und vorherige Auswertungen bleiben erhalten. Neue Diagnose liegt versioniert unter E:\SolarCheck-PVIS-Training\instance-validation\<evaluation_id>; der letzte abgeschlossene neue Bericht zusätzlich in instance-validation.json. Der Index wird erst nach vollständigem Abschluss atomar ersetzt.

Strg+C bricht ab. Gleicher Instanzprüfstart prüft fertige Crop-Protokolle/Masken/Prüfsummen erneut und verwendet sie wieder, nur fehlende Crops erhalten Inferenz. Eine angebrochene Datei wird nicht als abgeschlossen gelesen. Bei Fehler bleibt der bisherige Abschlussindex erhalten. Gemeinsame OS-Sperre verhindert paralleles Schreiben mit dem Trainingspilot. Änderungen an Parent-Gewichten, Zahlenpaket, Profil oder ursprünglichem Ladecode werden abgewiesen; kein automatisches Ersatztraining.

## Methode, Nachweise und Grenzen

Experimentelles festes Profil pvis-embedding-fixedrange-256-1: PV-Wahrscheinlichkeit≥0,5; [OpenCV floodFill](https://docs.opencv.org/4.x/d7/d1b/group__imgproc__misc.html) mit FLOODFILL_FIXED_RANGE/FLOODFILL_MASK_ONLY, acht Nachbarn und Rasterreihenfolge der Startpixel. Zwei gelernte Instanzmerkmale, maximal0,5Abstand pro Merkmalsachse zum Startpixel. Dies ist ein ausdrücklich eigenes experimentelles Auswerteprofil, keine bestätigte Original-CVUT- oder Mean-Shift-Implementierung. Räumlich getrennte Regionen bleiben getrennt, gleiche Merkmale garantieren keine physische Identität. Kleine Regionen unter16Pixel verwerfen; spätestens512Regionen oder128Kandidaten pro Crop stoppen und diesen Crop unbewertet lassen. Grenzen/Schwellen sind fest, keine Anpassung mit Hilfe der Prüfanlage oder Referenzanzahl.

**Die Segmentierung erhält keine Referenzmaske, Ignoriermaske oder gewünschte Modulzahl.** Erst danach dient die Referenz zum Bewerten auf gültigen Pixeln. Vorhersagen ausschließlich in ignorierten Bereichen bleiben unbewertet; teilweise dort liegende Vorhersagen werden auf den gültigen Pixeln verglichen. Dadurch wird keine vollständige Modulgeometrie bestätigt. Ignorierte Streifen dürfen nicht nachträglich als Hilfe zum Auftrennen der Vorhersagen verwendet werden. Standardmäßige maximale bipartite Trefferzuordnung bei Masken-IoU≥0,5; keine Bibliotheksinstallation nötig.

27neue synthetische Vertragsfälle plus ein echter isolierter Torch-CPU-Fall bestanden: benachbarte Instanzen, feste statt verketteter Merkmalsdistanz, getrennte Regionen, Leerfälle/Grenzen, Zählgleichheit mit falschen Umrissen, Zusammenfassung/Teilung, Ignorieren ohne Referenzhilfe, Manipulation und Abbruch→Fortsetzung→Wiederöffnung ohne Nachtraining. Zusätzlicher vollständiger lokaler Regressionsblock192Tests. Kontrollgrafik der öffentlichen Probe gesichtet. Reale Windows10-Abnahme dieses neuen Auswertungswegs noch offen, ursprünglicher Trainingslauf bereits bestanden.

PVIS-Daten bleiben unter [CC BY4.0 / Anbieterangaben](https://zenodo.org/records/23886365), externe SHA-geprüfte U-Net-Referenz unter GPL3; veröffentlichte CVUT-Gewichte werden nicht geladen. Forschungsversuch angefordert, kommerzielle Rechteentscheidung weiterhin unreviewed. Keine Kunden-/SQLite-/Geotagänderung, kein Main-Merge. Thermal weiterhin **unvollständig: 280 von 287 Bildern**, Paarimport gesperrt, keine vollständige Abdeckung, Geometrie- oder Celsiusfreigabe. Keine1000manuellen Pflichtprüfungen.
