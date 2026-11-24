# Synthetische Trainingsprobe auf Windows 10

Stand 24.11.2026 · PV-SYNTHETIC-TRAIN-01 implementiert und synthetisch geprüft, reale Windows-10-Bedienabnahme offen. [Checkpoint](AKTUELLER_ENTWICKLUNGSSTAND.md).

Die gespeicherte Lernvorbereitung mit drei Modulflächen wurde laut Nutzer korrekt wiedergeöffnet. Der danach gestartete PV-Hawk-Vergleich verwendete dieselben veröffentlichten Gewichte wie zuvor:21Modellinstanzen/18Vorschläge/3von8Teilreferenzen. Lernmasken speichern trainiert kein Modell. Bitte diesen unveränderten Vergleich nicht erneut als Lernfortschritt testen.

Dieser neue Befehl qualifiziert die Trainingsmechanik: ausschließlich künstliche Bilder und zufällige Startgewichte, **keine Kundenbilder, privaten Lernmasken oder veröffentlichten CVUT-Gewichte**. Er öffnet **kein Programmfenster**, sondern gibt einen JSON-Bericht in PowerShell aus. Ein erfolgreicher Bericht ist kein neues PV-Erkennungsmodell und kein Qualitätsnachweis an einer Anlage.

## Was die Probe tatsächlich prüft

- Bestehende SHA-geprüfte externe U-Net-Referenz und getrennte Torch2.15.0-CPU-Laufzeit verwenden; kein eigener Netzaufbau und kein Modell-/Paketdownload. Die externe GPL-3.0-Referenz samt Lizenz bleibt separat im bisherigen Pilotordner; keine Produktions-/Weitergabefreigabe daraus ableiten.
- Vier im Speicher erzeugte64×64-RGB-Beispiele mit Masken0Hintergrund/1PV/255Ignorieren. Zwei Trainingsbeispiele, je ein Validierungs-/Prüfbeispiel, disjunkte deterministische synthetische Gruppen. Das ersetzt keine unabhängigen realen Anlagen. Der64×64-Test ist kein bestätigtes originales CVUT-Eingabeprofil.
- Drei echte SGD-Schritte durch die vollständige Referenz;64lernbaren Parametertensoren ändern sich im geprüften Lauf. Ignorierte Labels haben keinen direkten Verlustgradienten. Endliche Lernfehler werden dokumentiert, keine reale Trefferquote.
- Bestehende DatasetBuild-/TrainingRun-/execute_training-Herkunft verwenden. SHA-256 bindet Datenbeschreibung, Parameter und erzeugte Gewichte. Gewichte in eigenem neuen Probenordner speichern, mit weights_only=True/CPU/strikter118Tensorprüfung wieder laden; Validierungs-/Prüfausgaben müssen exakt übereinstimmen.
- Abbruch/Fehler vor Veröffentlichung entfernen nur den eigenen unvollständigen Lauf. Frühere abgeschlossene Proben bleiben unverändert. Erneutes Starten beginnt frisch ab festem Seed, setzt keinen Optimizerlauf fort. Bei hartem Beenden kann ein Ordner mit Endung.next bleiben; er wird nie als abgeschlossene Probe gelesen.

44gezielte Tests und14isolierte echte Torch-CPU-Fälle bestanden, einschließlich Abbruch während Training/nach Wiederladen, geänderter Referenz, Quellschutz und Wiederöffnung. Exakte finale Windows-/Linux-CI in PR9; reale Bedienabnahme separat.

## Start ohne Installation

Vorausgesetzt ist die bereits eingerichtete Umgebung **E:\SolarCheck-CVUT-KI-Pilot\env** mit dem vorhandenen vendor-Referenzordner. App-Python auf F:, OpenSfM, PV-Hawk, Projektdateien und SQLite bleiben unverändert. Der Startblock lädt nur eine feste geprüfte Quellcode-ZIP(ca.3MiB). Er installiert keine Pakete und verarbeitet keine Projektbilder. Jede erfolgreiche Probe erzeugt etwa119MiB synthetische Gewichte in E:\SolarCheck-CVUT-KI-Pilot\synthetic-training-probes.

Den vollständigen Block in **PowerShell** ausführen:

```powershell
$ErrorActionPreference = 'Stop'
$pvProbeCommit = 'SOURCE_COMMIT_PENDING'
$pvProbeStart = Join-Path 'E:\SolarCheck-Trainingsprobe-Start' $pvProbeCommit
New-Item -ItemType Directory -Force -Path $pvProbeStart | Out-Null
$pvProbeZip = Join-Path $pvProbeStart 'SolarCheck-source.zip'
Invoke-WebRequest -UseBasicParsing -Uri "https://codeload.github.com/multicoptermedia-ship-it/MCM-SolarCheck/zip/$pvProbeCommit" -OutFile $pvProbeZip
if ((Get-FileHash -Algorithm SHA256 $pvProbeZip).Hash.ToLowerInvariant() -ne 'SOURCE_SHA256_PENDING') {
    throw 'QuellZIP-Pruefsumme stimmt nicht. Nicht gestartet.'
}
Expand-Archive -LiteralPath $pvProbeZip -DestinationPath $pvProbeStart -Force
$pvProbeSource = Join-Path $pvProbeStart "MCM-SolarCheck-$pvProbeCommit"
& 'E:\SolarCheck-CVUT-KI-Pilot\env\Scripts\python.exe' (Join-Path $pvProbeSource 'scripts\MCM_SolarCheck_PV_TRAININGSPROBE.py') --prefix 'E:\SolarCheck-CVUT-KI-Pilot'
```

QuellZIP-Nachweis wird vor Übergabe mit festem Commit/Bytes/SHA und remote bytegleichen Runtime-/Konfigurations-/Paketdateien ergänzt.

## Ergebnis lesen und erneut öffnen

Erwartet sind check=solarcheck-pv-synthetic-training-1, status=passed, synthetic_only=true, synthetic_training_started=true, synthetic_weights_changed=true, changed_parameter_tensors=64, ignore_gradient_verified=true und reload_verified=true. customer_training_started/customer_images_read/published_weights_loaded/model_updated/production_approved und Fachflags bleiben false. Die allgemeine model_updated-Angabe bezieht sich auf bestehende Erkennermodelle; die gesonderten synthetic_…-Angaben dokumentieren die tatsächlich geänderten Testgewichte.

**Nur den ausgegebenen JSON-Text mitteilen**, keine Bilder oder privaten Berichte. Das Artefakt **SYNTHETIC_ONLY_NOT_A_PV_MODEL.pt** darf nicht als Modellbeschreibung im KI-Vergleich ausgewählt werden. Es wird keinem Erkennungsmodell zugeordnet.

Anschließend PowerShell schließen und den letzten abgeschlossenen Bericht mit folgendem Befehl erneut prüfen. **--show startet kein Training** und lädt auch kein Modell; Herkunft und Gewichtsdatei werden gelesen/SHA-geprüft:

```powershell
& 'E:\SolarCheck-CVUT-KI-Pilot\env\Scripts\python.exe' 'E:\SolarCheck-Trainingsprobe-Start\SOURCE_COMMIT_PENDING\MCM-SolarCheck-SOURCE_COMMIT_PENDING\scripts\MCM_SolarCheck_PV_TRAININGSPROBE.py' --prefix 'E:\SolarCheck-CVUT-KI-Pilot' --show
```

probe_id/run_id/weights_sha256 und die Messwerte müssen dabei unverändert bleiben. Ein weiterer Aufruf **ohne --show** erzeugt hingegen einen neuen Lauf. Fehler liefern einen separaten JSON-Diagnoseblock ohne rohe lokale Pfade; vorhandene Erkennungsmodelle und Proben bleiben erhalten.

## Offene Verbindung zum echten Nachtraining

Die Probe bestätigt weder PV-Hawk-Nachtraining noch die originale CVUT-Vorverarbeitung oder eine bessere Feldqualität. Vor tatsächlichem Nachtraining sind geeignete öffentliche bzw. ausdrücklich genehmigte Daten, Modell-/Daten-/Weitergaberechte, vollständige Beschriftungen samt Ausnahmen, ein qualifizierter Daten-/Traineradapter und ein unabhängiges reales Prüfset zu verbinden. Drei Module einer Anlage reichen nicht als allgemeiner Qualitätsnachweis. Bestehende Einwilligungs-/Freigabe-/Gruppenverträge bleiben maßgeblich. Kundenbilder bleiben lokal; keine Pflicht1000Module einzeln zu prüfen. Die unvollständige Thermal-Teilvorschau bleibt280/287, mit ihren GeoTIFF-Tags und der regulären Paarimport-Sperre.

Nutzerhinweis24.11.: [Datature und verlinkte Quellen geprüft](PV_SEGMENTATION_DATATURE_REVIEW.md). SAHI/SAM2/Belichtungsvarianten sind konkrete Prüfoptionen nach diesem Techniknachweis; kein neues Paket oder Feldmodell daraus automatisch übernommen.
