# Open-Source-Richtlinie für lokale SolarCheck-KI-Modelle

## Verbindliches Entwicklungsziel

Keine verpflichtende Cloud, kein kostenpflichtiger Modell-API-Zugang,
kein kostenpflichtiges KI-Abonnement und keine ungeklärten kommerziellen
Gewichte. Der normale Offline-Desktop bleibt **ohne** PyTorch, TorchVision
oder einen KI-Trainingsdienst installierbar. Mitgeteilte Nutzerpräferenz:
Windows 10 bleibt das bevorzugte Zielsystem.

Für den ersten experimentellen Klassifikationspfad werden die offenen
Projekte **PyTorch** und **TorchVision** verwendet. Hauptprojektlizenz:
BSD-3-Clause. **Wichtig:** Die tatsächlichen Pakete können weitere
Third-Party-Lizenztexte enthalten. Die Lizenzpflichten müssen mit den
tatsächlich auszuliefernden Wheels und ihren Abhängigkeiten dokumentiert
werden. Dies ist eine technische Vorauswahl, keine anwaltliche
Freigabe oder Garantie, dass jedes zukünftige Modell/Gewicht/Dataset
kostenfrei kommerziell nutzbar ist.

Referenzen zu den Projekten:
- PyTorch Quellcode/Lizenzen: https://github.com/pytorch/pytorch
- TorchVision Quellcode/Lizenzen: https://github.com/pytorch/vision
- Hinweise zu eigenen Nutzungsbedingungen von vortrainierten Gewichten:
  https://docs.pytorch.org/vision/master/models.html

MMDetection und YOLOX mit Apache-2.0-Projektlizenz bleiben **künftige
Kandidaten** für Objekterkennung. Hier wurden sie weder installiert noch
eingebaut. Für Ultralytics AGPL-/Enterprise-Varianten gibt es keine
automatische Abhängigkeit; falls später überhaupt relevant, gesonderte
juristische und technische Entscheidung.

## Tatsächlich implementierter OSS-Basispfad

`services/offline_torchvision_classifier.py` kann nach **bewusster
lokaler Einrichtung** ein `torchvision.models.resnet18(weights=None,
num_classes=...)`-Netz mit Zufallsgewichten auf dem eigenen PC erzeugen.
Die Ersteinrichtung speichert nur den tensorbasierten `state_dict`
auf dem Rechner und legt daneben ein lokales JSON mit SHA-256,
Framework-Versionen, Klassenzahl, Seed und Herkunftsangabe
„generated on this PC without pre-trained weights“ an.
**Keine fremden vortrainierten Modellgewichte, keine Hub-Downloads, keine
Hintergrundinstallation.** Die Bezeichnung „lokal initialisiert“ ist
keine digitale Signatur; wer beide Dateien manipuliert, kann deren
einfachen Prüfsummennachweis ebenfalls fälschen.

Ein explizites `offline-ai-config.json` im Ordner der produktiven
Offline-Projektdatenbank aktiviert ausschließlich diese lokale
`torchvision-resnet18-local-init`-Variante. Der Setup-Befehl ist
ein gesonderter Bedienerschritt. Ohne Konfiguration entstehen
keine Modellgewichte und kein TorchVision-Import auf dem Desktop;
bei ungültiger Konfiguration startet der normale Desktop ohne
KI-Training statt mit unbelegtem Modell. Das ist keine Aussage,
dass die komplette Windows-10-Installation generell telemetriefrei wäre.

Der optional injizierte Backend-Adapter verbindet die vorhandenen
`OfflineTrainingJobs` mit **echten lokalen PyTorch-Lernschritten**
auf CPU: maximal 30 Epochen, nur überprüfte Trainings-/Validierungs-/
Testkopien und die zuvor dokumentierten Nutzungsrechte,
Klassifikations- statt Detektions-/Segmentierungslabels,
`torch.load(..., weights_only=True)`, striktes Laden des passenden
Modellzustands, erneute Bildhash-Prüfung bei jedem Lesen, kooperative
Abbruchabfrage, zurückhaltende Ressourcen-/Bildgrößengrenzen,
separate Evaluierung von Validation und bis zum Ende unbenutztem Test.
Das experimentell erzeugte `.pt`-Gewicht bleibt ausdrücklich
**nicht in SolarCheck als Auswertungsmodell aktiviert**.
Erzeugte `training-metrics.json` enthält technische Kennzahlen,
keine Garantie der Fehlererkennungsqualität.

## Lokale optionale Installation unter Windows 10

Die reguläre Python-3.11-Offlineumgebung zuerst wie in
`INSTALLATION.md` installieren. Danach auf einem **getrennten,
verbundenen** Windows-x64-Rechner aus dem identischen Repository:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\prepare_windows10_ai_wheels.ps1 -Wheelhouse "C:\SolarCheck-AI-Wheels"
```

Das Vorbereitungsskript liest ausschließlich
`requirements-offline-ai.txt`. Es lädt optionale Pakete samt
Abhängigkeiten, erstellt das existierende SHA-256-Wheelhouse-Manifest
und verändert die Kern-Requirements nicht. Die PyTorch-/TorchVision-
Pakete können mehrere hundert MB umfassen. Auf dem **getrennten,
offline betriebenen Windows-10-Zielrechner** nach geprüfter
Übertragung des gesamten Ordners:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_windows10_ai_wheels.ps1 -Wheelhouse "D:\SolarCheck-AI-Wheels"
```

Das Zielskript verwendet nur `pip --no-index --find-links`, prüft das
lokale Manifest und `pip check` und erzeugt absichtlich **keine**
Modellgewichte. Ein vorhandenes, anderweitig geprüftes lokales Wheel
muss nur dann in das optionale Paket aufgenommen werden, wenn die
tatsächliche Torch-/TorchVision-Installation es benötigt. Vor
Produktivbetrieb Versionen, zusätzliche Lizenzen, Windows-10-CPU-
Kompatibilität und Vertrauenswürdigkeit der Wheelquelle prüfen.
Der SHA-256-Manifestbestand ist **keine** Signatur oder
vollständige Supply-Chain-Sicherheitsgarantie.

## Bediente Aktivierung ohne Modell-Download

Die eigentliche Offline-Projektdatenbank muss bereits existieren. Im
Projektverzeichnis `PYTHONPATH=src` bereitstellen und mit der
lokalen `.venv` ausführen (Beispielpfad anpassen):

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mcm_solarcheck.offline.ai_setup initialize --database "C:\Users\Nutzer\MCM-SolarCheck\solarcheck.sqlite3" --classes 2 --seed 41 --epochs 1
.\.venv\Scripts\python.exe -m mcm_solarcheck.offline.ai_setup verify --database "C:\Users\Nutzer\MCM-SolarCheck\solarcheck.sqlite3"
```

Die **Klassenanzahl muss exakt zur späteren, tatsächlich geprüften
Trainingsauswahl passen**. Setup überschreibt niemals ein vorhandenes
Modell-/Policy-Paar. Nach aktiviertem Policy-Eintrag und tatsächlicher
separater Trainingsfreigabe kann ein lokaler klassifizierender
Trainingsauftrag starten, aber nur bei genügend geprüften und für das
Training zulässigen Beispielen mit geeigneten disjunkten Splits.

**Weder ein angekreuztes Trainingsfeld noch eine hohe Testgenauigkeit
sind eine automatisch validierte PV-Diagnose.** Es gibt weiterhin
keine freigegebene radiometrische Temperaturmessung aus falschfarbigen
JPGs, keine automatische geometrische Fehlerlokalisierung, keine
trainierte Produktionsmodell-Freigabe und keinen unter realen
Windows-10-/Mavic-3T-Daten wissenschaftlich validierten Trainingslauf.

## Abnahmegrenzen

Die CI installiert Torch/TorchVision derzeit **nicht** mit: Die
laufenden Windows-/Ubuntu-Regressionsjobs prüfen Lizenz-/Pfad-/Hash-
und Setup-Grenzen ohne hohe Downloads. Der tatsächliche PyTorch-
Trainingslauf, Herkunft und Drittkomponentenlizenz der konkreten
Wheels sowie reale Windows-10-Hardware sind erst in einer
separaten optionalen End-to-End-Abnahme zu testen. Auch ein
lokal trainiertes ResNet18-Modell auf sehr kleinen Datenmengen
ist keinesfalls eine belegte SolarCheck-Erkennungsfunktion.
