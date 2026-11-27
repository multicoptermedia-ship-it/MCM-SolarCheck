# Mit mehr öffentlichen Ausschnitten kontrolliert weiterlernen

**Entwicklungsbefund: technisch abgeschlossen, Erkennungsqualität unzureichend. Den unten dokumentierten Forschungsstart derzeit nicht als nächsten Nutzerlauf ausführen.** Die öffentliche608-Schritte-Probe ist hier bereits beendet; die Auswahl liefert0Treffer bei117Referenzmodulen. Weitere identische lokale Lernläufe helfen uns damit nicht. Der nächste fachliche Weg ist die Prüfung eines bereits auf PV-Modulinstanzen trainierten Standardmodells. Die vorhandenen Ergebnisse bleiben erhalten.

Stand27.11.2026 · PVIS-CONTROLLED-LEARNING-01 · [Entwicklungsstand](AKTUELLER_ENTWICKLUNGSSTAND.md).

Dein Technikpilot, die Instanzprüfung und deren Wiederöffnung sind abgeschlossen. Die Instanzprüfung hat3von8Crops vollständig ausgewertet:15Referenzen/5Vorschläge/0Treffer;5Crops unbewertet. Die sauber eingefärbten Module im Kontrollbild waren die Referenz, die Vorhersage noch stark gestört. **Diese Schritte nicht wiederholen.**

Jetzt werden alle58geeigneten Trainingsausschnitte aus Anlage009 und24fest ausgewählte Validierungsausschnitte aus033 verwendet. Die bisherigen acht Validierungscrops sind die ersten acht dieser24; ihre Rohflächen-IoU bleibt separat vergleichbar. Der größere Bestand enthält328Trainings- und117Validierungs-Modulbeobachtungen, keine eindeutigen physischen Modul-IDs. Prüfanlage024 und Kundendaten bleiben unangetastet.

Vorhandenes F:-App-Python und E:-Torch-CPU werden weiterverwendet. **Keine Installation und keine neuen Bilder-/Modelldownloads.** Nur die neue QuellZIP wird geladen. E:\SolarCheck-PVIS-Lernen ist ein eigener Ordner; alte Gewichte, Berichte und Quellen bleiben erhalten. Für atomare Modell-/Adam-Speicherpunkte mindestens **1,1GB freien Platz auf E:** vorsehen, zusätzlich etwa20MB für den öffentlichen Zahlenkorpus.

## Start

Den vollständigen Block in PowerShell ausführen. Er bereitet den größeren öffentlichen Zahlenkorpus vor und startet anschließend ausdrücklich die längere Lernphase:

```powershell
$ErrorActionPreference = 'Stop'
$pvLearnCommit = 'b94d3bd01810e27e379cb1aeb575bb4e65fd80cb'
$pvLearnStart = Join-Path 'E:\SolarCheck-PVIS-Lernen-Start' $pvLearnCommit
New-Item -ItemType Directory -Force -Path $pvLearnStart | Out-Null
$pvLearnZip = Join-Path $pvLearnStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvLearnCommit" -OutFile $pvLearnZip
if ((Get-FileHash -Algorithm SHA256 $pvLearnZip).Hash.ToLowerInvariant() -ne '77dfce82eb789b60a612d8a3ecd13fea053b7bd9a45fdb9ba034ff279d16b888') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvLearnZip -DestinationPath $pvLearnStart -Force
$pvLearnSource = Join-Path $pvLearnStart "MCM-SolarCheck-$pvLearnCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pvLearnSource 'scripts\MCM_SolarCheck_PVIS_LERNEN.py') --learn-public --source-prefix 'E:\SolarCheck-PVIS-Referenz' --parent-prefix 'E:\SolarCheck-PVIS-Training' --prefix 'E:\SolarCheck-PVIS-Lernen' --torch-prefix 'E:\SolarCheck-CVUT-KI-Pilot' --session-minutes 20
```

Feste Quelle b94d3bd01810e27e379cb1aeb575bb4e65fd80cb, ZIP 3321182 Bytes, SHA256 77dfce82eb789b60a612d8a3ecd13fea053b7bd9a45fdb9ba034ff279d16b888. Laufzeitquellen und Konfiguration gegen das remote geladene Archiv geprüft; exakte finale HEAD-CI in Draft PR9.

Die Vorbereitung zeigt82Crop-Fortschritte. Dabei werden vorhandene öffentliche JPEGs erneut gelesen, um die bereits geprüften Fenster als Zahlen zu speichern; die abgeschlossene Bildadapterprüfung wird nicht erneut ausgeführt. Fertige Crop-Dateien werden bei Fortsetzung geprüft und wiederverwendet. Der bisherige512→256-RGB-/Instanz-/Ignoriervertrag bleibt unverändert. Keine andere Normalisierung.

Danach prüft das vorhandene Torch-Python zunächst die Ausgangsgewichte auf den24Validierungscrops. Anschließend erscheinen **Lernspeicherpunkt**- und **Kontrolliertes Lernen: Epoche…**-Zeilen. Ergebnisse erscheinen in PowerShell; ein Kontrollbild wird erst nach Abschluss aller Epochen erzeugt.

## Zeitgrenze, Abbruch und Fortsetzung

Ein Start hat **bis zu20Minuten Rechenzeit**, zuzüglich Abschluss eines gerade laufenden Schritts, einer Validierungsrunde oder Speicherung. Die vorbereitende Datenprüfung zählt nicht zur Lernzeit. Nach der Zeitgrenze endet der Prozess, kein Hintergrund-/Nachtlauf. Insgesamt maximal acht Epochen, bei diesem Bestand76Updates je Epoche/608Updates insgesamt. Kein automatisches endloses Neustarten.

**status=checkpoint_available** bedeutet einen gespeicherten Zwischenstand. saved_steps bezeichnet dauerhaft gespeicherte Updates. completed_epochs und next_sample zeigen die genaue Position. Derselbe Startblock setzt dort mit Modell, Adam-Momenten, Zufallszustand und Teilergebnissen fort. Das ist keine neue Zufallsinitialisierung und kein erneuter24-Schritte-Technikpilot.

Alle16Updates und nach vollständigen Epochen wird ein neuer versionierter Speicherpunkt geschrieben; erst danach wird die Hashreferenz atomar ersetzt. Die letzte vollständige Version bleibt bis dahin erhalten. Strg+C verwendet ebenfalls den letzten vollständigen Speicherpunkt; eine noch nicht gespeicherte Teilstrecke wird beim nächsten Start wiederholt. Ein Abbruch während der ersten Initialisierung kann erneut bei Schritt0 beginnen. Quellen-/Daten-/Profiländerungen werden abgewiesen und nicht stillschweigend als Fortsetzung behandelt.

Bitte nicht parallel eine zweite Sitzung oder --show starten. Die gemeinsame OS-Sperre schützt den neuen Lernordner und den gelesenen alten Pilotstand. Der private PV-Vergleich wird durch diesen Ablauf nicht verändert.

## Vollständiger Befehl für den gespeicherten Bericht

Nach Ende der Sitzung, auch nach einer Zeitpause, PowerShell schließen und erneut öffnen. Dann diesen vollständigen Befehl ausführen:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Lernen-Start\b94d3bd01810e27e379cb1aeb575bb4e65fd80cb\MCM-SolarCheck-b94d3bd01810e27e379cb1aeb575bb4e65fd80cb\scripts\MCM_SolarCheck_PVIS_LERNEN.py' --prefix 'E:\SolarCheck-PVIS-Lernen' --parent-prefix 'E:\SolarCheck-PVIS-Training' --show
```

--show prüft Parent-Lauf, Zahlenkorpus, Quellbindung, Speicherpunkt beziehungsweise ausgewählte Gewichte und fertige Kontrollbilder. **Kein Torch-Modell, neues Training oder neue Inferenz.** Der Bericht bleibt innerhalb derselben Umgebung identisch. Bitte den JSON-Text mitteilen; keine Bilder, ZIPs oder Gewichte hochladen.

Bei checkpoint_available kann derselbe Startblock die nächste begrenzte Sitzung ausführen. Vor einer weiteren Sitzung reicht zunächst der --show-Bericht, damit wir Fortschritt und Laufzeit prüfen können. Bei einem Diagnoseblock nur diesen Text mitteilen; kein Setup oder alten Pilot wiederholen.

## Abschluss und Kontrollbilder

**status=finished_experimental_not_production** heißt: acht Epochen abgeschlossen, ausgewählte Gewichte erneut geladen und deren Validierungsausgaben exakt geprüft. Derselbe Start öffnet anschließend den fertigen Bericht und trainiert nicht erneut.

candidate_step bezeichnet die anhand der Validierung ausgewählte Version. Sie kann vor dem letzten Lernschritt liegen oder bei ausbleibender Verbesserung die Ausgangsversion0 bleiben. experimental_weights_changed beschreibt die Änderung während der Lernphase; model_updated=false bedeutet, dass die bestehenden Erkennungsmodelle erhalten bleiben. **Noch kein Modellmanifest im privaten KI-Vergleich auswählen.**

Fertige Kontrollbilder liegen unter E:\SolarCheck-PVIS-Lernen\runs\<run_id>\preview-01.png bis preview-24.png. Den Laufordner findest du über run_id im Bericht oder active.json im Lernordner. Vier Spalten: RGB, vorgegebene Referenz(Magenta ignoriert), eigene Vorhersage, PV-Wahrscheinlichkeit. Die zweite Spalte ist keine KI-Erkennung. Das erste Kontrollbild nach erfolgreichem Abschluss öffnen:

```powershell
$pvLearnActive = Get-Content -LiteralPath 'E:\SolarCheck-PVIS-Lernen\active.json' -Raw -Encoding UTF8 | ConvertFrom-Json
$pvLearnRun = Join-Path 'E:\SolarCheck-PVIS-Lernen\runs' $pvLearnActive.run_id
$pvLearnImage = Join-Path $pvLearnRun 'preview-01.png'
if (Test-Path -LiteralPath (Join-Path $pvLearnRun 'report.json')) {
    Invoke-Item -LiteralPath $pvLearnImage
} else {
    Write-Host 'Zwischenstand vorhanden; Kontrollbilder entstehen nach Abschluss aller Epochen.'
}
```

## Lernmethode und Bewertung

Ausgangspunkt sind die eigenen bisherigen öffentlichen Vierkanal-U-Net-Gewichte; veröffentlichte CVUT-Gewichte werden nicht geladen. Bestehende SHA-geprüfte externe GPL3-U-Net-Referenz21d7850f, ursprünglicher Verlust, Datenreduktion und Instanzdecoder bleiben unverändert. Kein neuer Netzentwurf und keine Installation. Die38Einzelmodul-/20Mehrmodul-Trainingscrops werden abwechselnd verarbeitet, alle Quellen pro Epoche mindestens einmal; die kleinere Gruppe wird zur Angleichung wiederholt.

Trainingsbilder und Masken werden gemeinsam exakt um90Grad gedreht beziehungsweise horizontal gespiegelt. Beide Mengen erhalten alle acht Varianten unabhängig davon, ob ein oder mehrere Module enthalten sind. Nur Training, keine Interpolation oder Belichtungsänderung; unbekannte Pixel bleiben unbekannt. Maskierte Kreuzentropie und vorhandener diskriminativer Instanzverlust, direkte Ignoriergradienten in allen vier Ausgaben null. Faltungen können weiterhin Kontext aus unbeschrifteten Bildteilen nutzen. AdamW mit fester Lernrate0,0003/Gewichtsabnahme0,0001, Gradientenbegrenzung1; keine freie Parameter- oder Prüfanlagenoptimierung.

Die Auswahl erfolgt auf der Validierungsanlage033: zuerst vollständig segmentierbare24Crops, dann deren Instanz-F1, danach die Rohflächen-IoU aller24. Sind nicht alle Crops vollständig segmentierbar, wird keine Teilmengen-F1 als Gesamtleistung zur Auswahl benutzt. Kennzahlen vollständig segmentierter Teilmengen bleiben ausdrücklich solche Teilmengen. Nicht mit Vollabdeckung oder unabhängiger Abschlussprüfung gleichsetzen. Anlage024 bleibt für die spätere Abschlussprüfung reserviert.

raw_foreground_iou_all bezieht sich auf alle24Crops und kann auch bei einer unvollständigen Instanzsegmentierung gemessen werden. previous_first8_foreground_iou verwendet genau die bisherigen acht Validierungscrops. Instanz-F1 und Rohflächen-IoU messen verschiedene Eigenschaften. best/selected_validation ist eine Entwicklungsbewertung auf wiederverwendeter Validierung, keine allgemeine Qualitätsquote oder Freigabe.

Rechteentscheidung bleibt unreviewed, Daten unter[CC BY4.0/Anbieterangaben](https://zenodo.org/records/23886365), Referenzcode GPL3. Ursprüngliche Quellen, Privatprojekt/SQLite und Modelle bleiben erhalten. Keine automatische Kundenanalyse oder bestätigte physische Modulzahl. Thermal weiterhin **unvollständig: 280 von 287 Bildern**, GeoTIFF-Tags/Paarimport-Sperre/eigene Thermalposen erhalten. Keine Abdeckungs-, Geometrie- oder Celsiusfreigabe, kein Main-Merge und keine1000manuellen Pflichtreviews.

## Nachweise

26neue synthetische Vertragsfälle sowie ein echter isolierter U-Net-/Adam-Fall für Abbruch/Fortsetzung und exakt gleichen Endzustand wie bei ununterbrochenem Lauf bestanden; Zeitpausen-/Wiederöffnungs-/Quellschutzprüfung ergänzt. 218gezielte Vertrags-/Regressions-/Übergabetests grün; endgültiger öffentlicher --show-Bericht identisch. Neue exakte HEAD-CI und vollständiger öffentlicher Lernbefund werden getrennt in PR9 festgehalten. Reale Windows10-Abnahme des neuen längeren Lernwegs noch offen.

Öffentliche Probe abgeschlossen: Korpus58/24 mit328/117Modulbeobachtungen;21Updates gespeichert, --show identisch, Fortsetzung bis608Updates/acht Epochen erfolgreich, gewählte Ausgaben nach erneutem Laden exakt gleich. Rune99de2919aa96cf8cf54139d8ccf3779bbc2235b1289b063da291d136c3d3936. Ausgewählter KandidatSchritt76:117Referenzen/38Vorschläge/0Treffer, Rohflächen-IoU0,02353. Die Auswahlregel priorisiert vollständig segmentierbare Crops; dies ist keine Zusicherung besserer Erkennung, auch leere oder falsche Ergebnisse können vollständig berechenbar sein.

Eine getrennte Diagnose mit eingefrorenen Schritt592-Gewichten untersucht den Unterschied zwischen gespeicherten BatchNorm-Statistiken und Statistik je Einzelbild. Auf den ersten acht Validierungscrops erhöht sich die Rohflächen-IoU von0,01934 auf0,37937; der bisherige Instanzdecoder bleibt unzureichend. Ein festes semantisches Verfahren (PV≥0,5,Opening3,Komponenten≥16Pixel) auf allen24Crops trifft19der117Referenzmodule, erzeugt277weitere Vorschläge und übersieht98. Kein Kundenmodell und keine globale Qualitätsquote. Die Diagnose ändert keine gespeicherten Gewichte; keine Bildnormalisierung oder Belichtungskorrektur am Original. [Öffentlicher Zahlenbeleg](evidence/pvis-controlled-learning-2026-11-27.json).

Die offizielle[CVUT-Seite](https://imr.ciirc.cvut.cz/Datasets/PVsegmentation) nennt neben U-Net bereits trainierte **YOLOv8n PV module segmentation models (34MB)**. Der direkte Anbieterabruf liefert hier HTTP503. Der Nutzer hat die genaue offizielle[Downloadadresse PV_YOLOv8_models.zip](https://imr.ciirc.cvut.cz/uploads/Datasets/PV_YOLOv8_models.zip) mitgeteilt; auch dieser direkte Abruf liefert hier HTTP503. Er prüft zunächst die im ZIP enthaltenen Dateinamen lokal. Zuerst konkretes RGB-Artefakt, Code-/Gewichtsbedingungen und CPU-Laufzeit klären, dann gegen dieselbe öffentliche Validierung bewerten. Die CC-BY4.0-Erklärung der Seite gilt ausdrücklich dem Datensatz; daraus keine pauschale Modell-/Ultralytics-/Produktlizenz ableiten. Noch keine neue Installation oder proprietäre Produktfreigabe.
