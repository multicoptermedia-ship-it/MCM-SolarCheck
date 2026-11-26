# Begrenzter Trainingspilot mit öffentlichen PV-Modulen

**Training und Wiederöffnung real Windows10-PASS26.11.2026:** beide Nutzerberichte identisch. Nicht erneut trainieren. Weiter mit der [Instanzprüfung vorhandener Gewichte](PVIS_INSTANZPRUEFUNG_WINDOWS10.md). Die folgende Startanleitung bleibt als Nachweis erhalten.

Stand 26.11.2026 · PVIS-PUBLIC-TRAIN-01 · [Entwicklungsstand](AKTUELLER_ENTWICKLUNGSSTAND.md).

Dein Bildadapterbericht und beide Kontrollbilder sind geprüft. Diesen Schritt **nicht wiederholen**. Jetzt trainiert erstmals ein eigener begrenzter Versuch mit den vorhandenen öffentlichen RGB-Bildern. Er verwendet acht Trainingsausschnitte aus Anlage 009 und acht Validierungsausschnitte aus Anlage 033. Die Prüfanlage 024 bleibt als Bild unangetastet.

Vorhandenes App-Python auf F: und vorhandene Torch-CPU-Umgebung unter E:\SolarCheck-CVUT-KI-Pilot werden weiterverwendet. **Keine Installation, kein neuer Bilder- oder Modelldownload.** Nur die feste SolarCheck-QuellZIP unten wird geladen. Für getrennte numerische Daten, Speicherpunkte und Versuchsgewichte mindestens 400 MB auf E: frei halten. Das Skript öffnet kein Programmfenster; Fortschritt und Ergebnis erscheinen in PowerShell.

## Start

Den vollständigen Block in PowerShell ausführen. **--run-public-pilot startet ausdrücklich echtes Training auf öffentlichen Daten.** Keine Kundendaten oder private Lernmasken werden gelesen.

```powershell
$ErrorActionPreference = 'Stop'
$pvTrainCommit = '825cd57dcae617b3b3a03f34e1be980d7d48cc7b'
$pvTrainStart = Join-Path 'E:\SolarCheck-PVIS-Training-Start' $pvTrainCommit
New-Item -ItemType Directory -Force -Path $pvTrainStart | Out-Null
$pvTrainZip = Join-Path $pvTrainStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvTrainCommit" -OutFile $pvTrainZip
if ((Get-FileHash -Algorithm SHA256 $pvTrainZip).Hash.ToLowerInvariant() -ne '637b544f35d9977f44838c349749b165592b76a60cb24ac5a153ec4a0b21f452') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvTrainZip -DestinationPath $pvTrainStart -Force
$pvTrainSource = Join-Path $pvTrainStart "MCM-SolarCheck-$pvTrainCommit"
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' (Join-Path $pvTrainSource 'scripts\MCM_SolarCheck_PVIS_TRAINING.py') --run-public-pilot --source-prefix 'E:\SolarCheck-PVIS-Referenz' --torch-prefix 'E:\SolarCheck-CVUT-KI-Pilot' --prefix 'E:\SolarCheck-PVIS-Training'
```

Feste Quelle 825cd57dcae617b3b3a03f34e1be980d7d48cc7b, ZIP 3267779 Bytes, SHA256 637b544f35d9977f44838c349749b165592b76a60cb24ac5a153ec4a0b21f452. Quellcode und Konfiguration werden gegen das heruntergeladene Archiv geprüft; exakte finale HEAD-CI in Draft PR9.

Zuerst prüft das App-Python den abgeschlossenen Adapterstand. Nur die 16 fest ausgewählten öffentlichen Ausschnitte werden erneut dekodiert und gegen ihre gespeicherten Pixel-/Maskenprotokolle geprüft. Ihre primitiven Zahlenfelder bilden ein eigenes SHA-gebundenes NPZ-Paket; kein Pickle. Damit muss die getrennte Torch-Umgebung keine Bilder oder Masken mit abweichenden Bildbibliotheken neu berechnen. Originalarchive und bestehende Adapterberichte bleiben erhalten.

Danach startet automatisch das vorhandene Torch-Python. Drei Epochen mit jeweils acht Lernschritten, insgesamt 24 Schritte, sind fest vorgegeben. Nach jeder vollständig gespeicherten Epoche erscheint ein Fortschrittszähler. CPU-Ausführung kann mehrere Minuten dauern; die tatsächliche Windows10-Laufzeit ist noch offen. Keine freie Parameterwahl und kein Nachtrainieren auf der Prüfanlage.

## Ergebnis und Wiederöffnung

Erwartete Kernwerte nach erfolgreichem Abschluss:

```json
{
  "check": "solarcheck-pvis-instance-training-1",
  "status": "finished_experimental_not_production",
  "split_counts": {"train": 8, "validation": 8},
  "epochs_completed": 3,
  "steps": 24,
  "training_started": true,
  "public_training_started": true,
  "experimental_weights_changed": true,
  "reload_verified": true,
  "ignore_gradient_verified": true,
  "pixel_test_images_read": 0,
  "customer_images_read": false,
  "model_updated": false,
  "instance_detection_ready": false,
  "production_approved": false
}
```

**model_updated=false bezieht sich auf die bisherigen Erkennungsmodelle.** Der Versuch erzeugt eigene neue Gewichte; experimental_weights_changed=true bestätigt deren Änderung. Diese Datei heißt EXPERIMENTAL_PVIS_INSTANCE_NOT_APPROVED.pt und liegt im eigenen Laufordner unter E:\SolarCheck-PVIS-Training\runs. **Noch kein Modellmanifest im RGB-/Thermal-KI-Vergleich auswählen.** Der Pilot liefert zunächst lernbare Flächen- und Instanzmerkmale; eine geprüfte Umwandlung in einzelne Modulvorschläge und belastbare Modulzählung folgt separat.

Nach Schließen und erneutem Öffnen von PowerShell diesen vollständigen Befehl ausführen:

```powershell
& 'F:\MCM-SolarCheck\.venv\Scripts\python.exe' 'E:\SolarCheck-PVIS-Training-Start\825cd57dcae617b3b3a03f34e1be980d7d48cc7b\MCM-SolarCheck-825cd57dcae617b3b3a03f34e1be980d7d48cc7b\scripts\MCM_SolarCheck_PVIS_TRAINING.py' --prefix 'E:\SolarCheck-PVIS-Training' --show
```

--show prüft Datenpaket, Laufbericht und Gewichtsprüfsumme ohne Torch-Modell, JPEG-Dekodierung oder neues Training. Der JSON-Bericht muss identisch bleiben. Bitte nur diesen JSON-Text mitteilen; keine Bilder, ZIPs oder Gewichtsdateien hochladen. Bei Fehler reicht der ausgegebene Diagnoseblock; keine Neuinstallation.

## Abbruch und Fortsetzung

Strg+C beendet den Versuch. Nur vollständig gespeicherte Epochen werden übernommen. Beim erneuten Ausführen desselben Startbefehls wird der letzte geprüfte Speicherpunkt mit Gewichten, CPU-Zufallszustand und Lernverlauf geladen. Eine angebrochene Epoche beginnt erneut. Mit festem SGD ohne Momentum und gleicher Quelle/Umgebung ist die Fortsetzung ab der Epochengrenze deterministisch; sie setzt nicht mitten in einem Lernschritt fort.

Speicherpunkte werden versioniert geschrieben und erst danach über eine atomare Hashreferenz veröffentlicht. Ein unvollständiger Folgeschreibvorgang zerstört den letzten vollständigen Speicherpunkt nicht. Geänderte Daten oder Speicherpunkte werden abgewiesen. Erst nach Abschluss einschließlich Gewichts-Wiederladeprüfung wird latest.json atomar auf den neuen Lauf gesetzt. Ältere abgeschlossene Läufe, bisherige Erkennungsmodelle, ursprüngliche Referenzberichte und Quellen bleiben erhalten. Eine gemeinsame OS-Sperre blockiert parallele Schreibläufe.

Ein bereits abgeschlossener identischer Versuch wird wieder geöffnet, nicht erneut trainiert. Eine andere Quelle oder Datenversion erhält eine neue Laufkennung.

## Technischer Umfang und Grenzen

Verwendet wird die bereits SHA-geprüfte externe GPL-3.0-U-Net-Referenz am Commit21d7850f2af30a9695bbeea75f3136aa538cfc4a. Der Versuch startet mit festem Zufallsseed und eigenem Vierkanalausgang: zwei Flächenlogits und zwei Instanzmerkmale. Veröffentlichte CVUT-Gewichte werden nicht geladen; deren Rechte und originales Eingabeprofil bleiben ungeprüft. Der bisherige Zweiklassen-CVUT-Vergleich bleibt erhalten.

Der Lernfehler verbindet maskierte Kreuzentropie mit dem [diskriminativen Instanzverlust von De Brabandere, Neven und Van Gool, 2017](https://arxiv.org/abs/1708.02551): Merkmale innerhalb desselben Moduls zusammenziehen und verschiedene Modulmittel auseinanderhalten. Ignorierte Pixel haben in allen vier Ausgabekanälen direkten Gradienten null. Das Modell kann trotzdem Bildkontext außerhalb beschrifteter Pixel über seine Faltungen verwenden.

Eigene Vorverarbeitung pvis-rgb-area256-instance-nearest-allvalid-1: native512-Auditausschnitte mit exakt definiertem 2×2-Flächenmittel auf256RGB-Pixel reduzieren; lokale Instanznummern per nächster Pixelmitte übernehmen. Sobald einer der vier beitragenden Quellpixel ignoriert ist, wird der Zielpixel ignoriert. RGB→float32/CHW/255, keine zusätzliche Belichtungsnormalisierung. Keine Behauptung eines originalen CVUT-Profils. Die veröffentlichten projizierten ganzen Modulflächen behalten ihre eigene Beschriftungsrichtlinie; private sichtbare Eckenumrisse werden nicht beigemischt.

Der Bericht enthält Lernfehler und Vordergrund-IoU auf genau diesen acht Validierungscrops. **Diese Flächenmetrik misst keine korrekte Anzahl oder Trennung der Module.** Sie ist keine allgemeine Genauigkeit oder vollständige Anlagenprüfung. Keine Behauptung verbesserter Kundenbilderkennung aus einem kurzen Versuch.

Technische Nachweise: 165 gezielte synthetische Vertrags-/Regressions-/Übergabetests bestanden, zusätzlich zwei echte Torch-CPU-Instanzfälle und die Zweiklassen-Vorwärtsregression. Die CPU-Probe prüft ID-Permutation, direkte Ignoriergradienten, Abbruch/Fortsetzung mit exakt gleichem Endzustand sowie gespeicherte und erneut geladene Ausgaben. CI verwendet ausschließlich erzeugte Testdaten.

Zusätzlicher echter öffentlicher Linux-Versuch mit genau8+8Crops abgeschlossen:24Schritte,59geänderte Parametertensoren, Wiederladen/--show identisch. Trainingsverlust1,8164→1,7692; Validierungsverlust8,5720→8,5583, Vordergrund-IoU0,2445→0,2054. **Noch keine Erkennungsverbesserung belegt.** Run85a4f283fdc648723d7d67d01e644126297cc666875cf574a2ea2b17cc5f810c; Gewichts-SHA256dffbd8d9c09e0f9592f746a43699dd9d3a101e9708c983d5d1ce6254428e4c17. Dies belegt die Trainingsverbindung, nicht einen fertigen Modulerkenner oder die reale Windows10-Trainingsabnahme.

Öffentliche Daten: PVIS-10K1.0.0, [Zenodo23886365](https://zenodo.org/records/23886365), [CC BY4.0 mit Urheberangaben des Anbieters](https://zenodo.org/records/23886365/files/LICENSE.md?download=1). Lokaler Forschungsversuch ist ausdrücklich angefordert; eine kommerzielle Rechteentscheidung wird dadurch nicht als bereits geprüft eingetragen. Lizenzentscheidung unreviewed, commercial_training_approved=false. Bei späterer Weitergabe Attribution, Lizenzlink und Änderungsangaben erhalten; externe Referenzsoftware und veröffentlichte Gewichte getrennt prüfen.

Kundendaten, produktive SQLite, RGB-/Thermal-Quellen und bestehende Modelle bleiben erhalten. Thermal bleibt **unvollständig: 280 von 287 Bildern**, einschließlich GeoTIFF-Metadaten und Sperre des regulären Paarimports. Keine vollständige Abdeckungs-, Geometrie-, Celsius- oder physische Modul-ID-Freigabe und keine 1000 manuellen Pflichtprüfungen.
