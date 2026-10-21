# MCM-SolarCheck – Installation

## Windows 10 Home – Offline-Desktop (Entwicklungsstand)

Diese Variante ist ausdrücklich für den bestehenden Windows-10-Auswertungsrechner
vorgesehen. **Keine Windows-11-Voraussetzung**, kein Online-Kundenkonto und
kein automatischer Download beim Start. Windows-10-Tests auf echter Hardware
bleiben für die Freigabe nötig; GitHub testet die Win32-Schnittstellen zunächst
unter Windows Server 2022.

1. 64-Bit-Python 3.11 installieren, Projektquellcode lokal bereitstellen.
2. Abhängigkeiten bei der Einrichtung einmalig installieren. Dazu ist ein
   Paket-Download oder ein zuvor vorbereiteter, lokaler Wheel-Ordner nötig:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Die **Offline-Anwendung** ohne Kunden-Online-Shell starten:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_windows10_offline.ps1
```

4. Den lokalen, nicht-schreibenden **Smoke-Test für die vorhandenen Projekte**
   ausführen: Dieser verwendet ausschließlich eine temporäre Testdatenbank,
   lädt nichts nach und prüft den GUI-Start und die offline gebundene Projektanlage.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\validate_windows10_offline.ps1
```

   Mit `-IncludeTests` wird zusätzlich die native Administrator-/DPAPI-/
   GUI-Testsuite ausgeführt; dazu muss `pytest` bereits in `.venv` installiert
   sein. Das Skript verweigert ausdrücklich andere Betriebssysteme. Es verändert
   nicht die globale PowerShell-Ausführungsrichtlinie.

5. Separaten lokalen Administrator nur bei Bedarf einrichten, **ohne
   Standardpasswort oder Kommandozeilen-Passwort**:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m mcm_solarcheck.offline.admin_setup
```

   Für alte Windows-v1-Anmeldedatensätze ist die Passwortbestätigung per
   `--migrate-legacy-windows` erforderlich. Die neue v2-Datei wird mit der
   Windows-DPAPI des aktuell angemeldeten Benutzerkontos geschützt. Ein anderer
   Windows-Benutzer kann sie nicht ohne weiteres übernehmen.

**Release-Grenzen:** Der aktuelle Programmstart erfolgt noch aus den Quellen.
Ein freigegebener, signierter Offline-`.exe`-Installer wird erst in einer
eigenen Packaging-Phase erstellt. Die CI testet echte Win32-APIs auf einem
Windows-Server-2022-Runner, **nicht** die tatsächliche Windows-10-Maschine,
nicht den Installer und nicht die DJI-Mavic-3T-Geräteintegration. Die
Smoke-Prüfung verbietet Python-Netzwerkverbindungen im getesteten Startablauf;
sie beweist **nicht**, dass das Windows-Betriebssystem oder jede Fremdbibliothek
generell keine Telemetrie erzeugt. Lokale Windows-Dateirechte, Backup und
Betriebssicherheit sind zusätzlich abzusichern. Windows 10 selbst erhält nicht
mehr den regulären Herstellersupport; die Wahl des Systems wird dadurch nicht
automatisch geändert.

### Windows 10: Python-Abhängigkeiten ohne Internet auf dem Zielrechner installieren

Die später geplante signierte `.exe` ist **noch nicht verfügbar**. Für den
aktuellen Quellcode-Entwicklungsstand kann jedoch bereits ein lokales
Wheel-Paket vorbereitet und auf den Windows-10-Rechner übertragen werden.

1. Auf einem **separaten, internetverbundenen Windows-x64-Rechner** mit
   **Python 3.11 (64 Bit)** denselben Quellcode und dieselbe
   `requirements.txt` verwenden. Im Repositoryordner ausführen:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\prepare_windows10_wheelhouse.ps1 -Wheelhouse "C:\MCM-Offline-Wheels"
```

   **Nur dieses Vorbereitungsskript** lädt mit `pip download` Python-Wheels
   samt Abhängigkeiten aus Paketquellen herunter. Es verweigert existierende
   Zielverzeichnisse, überschreibt keine früheren Paketsammlungen und
   erstellt `wheelhouse-manifest.json` mit Python-Zielkennung,
   `requirements.txt`-SHA256 und SHA256/Größe jedes Wheels.
   Den Paketordner **mitsamt Manifest** und exakt die passende
   Quellcode-Version auf vertrauenswürdigem Datenträger übertragen.

2. Auf dem **Windows-10-Zielrechner**, auf dem Python 3.11 (64 Bit) bereits
   vorhanden sein muss, die `.venv` nur dann neu einrichten, wenn dort
   **noch keine** `.venv` existiert:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\install_windows10_offline_venv.ps1 -Wheelhouse "D:\MCM-Offline-Wheels"
```

   Das Skript verifiziert vor Anlegen der `.venv` alle Dateien des
   Wheel-Pakets, den Zielinterpreter und den exakten
   `requirements.txt`-Inhalt. `pip` verwendet ausschließlich
   `--no-index --find-links`, prüft anschließend per `pip check`
   und startet einen temporären Offline-GUI-Smoke-Test. Es **löscht oder
   ersetzt keine vorhandene `.venv`**. Bei Fehlern kann eine unvollständige
   neue `.venv` verbleiben: nicht starten, sondern Ursache klären.

3. Danach die Desktopanwendung wie oben über
   `scripts/start_windows10_offline.ps1` starten. Ein Admin-Konto wird
   **nicht** automatisch provisioniert; echte PV-Projekte werden beim
   Installations-/Smoketest nicht verwendet.

**Sicherheitsgrenzen:** Ein SHA256-Manifest bestätigt die Übereinstimmung
mit dem vorbereiteten Ordner, ist jedoch **keine digitale Signatur**.
Wird der Manifestersteller oder beides manipuliert, erkennt diese Prüfung
den Angriff nicht. Download- und Quellcode-Herkunft müssen separat
vertrauenswürdig sein; ein Herstellerzertifikat, ein geprüftes
Abhängigkeits-Lockfile, eine Windows-10-Hardwareprüfung sowie die echte
reproduzierbare `.exe`-Distribution folgen erst zur Releasefreigabe.
Das bereits installierte Python 3.11 selbst gehört derzeit noch nicht
zum Offline-Paket. Auch der Paket-Build auf dem verbundenen Vorbereitungsrechner
ist keine Offline-Aktion.

### Optionaler Open-Source-KI-Trainer ohne kommerzielle Modellgewichte

Für die erste Klassifikationsstrecke unterstützt SolarCheck einen **opt-in**
und vollständig lokalen PyTorch-/TorchVision-Trainer. PyTorch und
TorchVision gehören **nicht** zur normalen `requirements.txt`.
Die Projektlizenz ist primär BSD-3-Clause; tatsächliche Wheel-/Dritt-
komponenten- und Modellgewichte-Lizenzen sind vor Weitergabe separat
zu prüfen. Es ist kein externer vortrainierter Checkpoint nötig:
`resnet18(weights=None)` initialisiert neue Modellgewichte lokal.

Die optionale Abhängigkeitsliste heißt `requirements-offline-ai.txt`.
Sie wird auf einem **verbundenen** Windows-3.11-x64-Vorbereitungsrechner
mit `scripts/prepare_windows10_ai_wheels.ps1` in ein separates Wheelhouse
geladen. Auf dem Offline-Windows-10-Zielrechner wird sie ausschließlich mit
`scripts/install_windows10_ai_wheels.ps1` aus geprüften lokalen Wheels
installiert. **Nie** diesen Download auf dem Auswertungsrechner starten.
Das ändert nicht die bestehende Datenbank, führt kein KI-Training aus
und ersetzt nicht den zukünftigen eigenständigen EXE-Installer.

Der Bediener kann anschließend explizit mit
`python -m mcm_solarcheck.offline.ai_setup initialize` (Parameter
`--database`, `--classes`, `--seed`, `--epochs`) lokal neue Gewichte
und die daneben liegende Model-Provenance sowie
`offline-ai-config.json` erzeugen; der Datenbankpfad muss existieren.
`verify` prüft anschließend die lokale Konfiguration.
Beispielbefehle und Sicherheitsgrenzen stehen in
`docs/OFFLINE_OSS_AI_LICENSE_POLICY.md`. `build_offline_window()`
verwendet nur eine vorher ausdrücklich aktivierte, passende lokale
Konfiguration; sonst bleibt Training aus.

Die CPU-Trainingsfunktion führt echte lokale Optimierung und beschränkte
Validation-/Testauswertung aus, **deployt das Ergebnis aber niemals
automatisch**. Unter Windows 10 und mit echten legal nutzbaren
PV-Bilddaten steht die Abnahme noch aus. Kein Recht zur
Kundendatennutzung ergibt sich aus der bloßen Open-Source-Lizenz.

## Ubuntu 22.04 / 24.04

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip libreoffice
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## First test

1. Enter a project name.
2. Click **Projekt anlegen**.
3. Import several RGB/thermal JPG/TIFF images.
4. Verify that GPS coordinates are displayed where EXIF GPS is available.
5. A tested YOLO model can be placed at `models/pv_defects.pt`.
6. Run **KI-Auswertung starten**.
7. Create the ODT report.

## Important production note

The current repository version is an MVP/scaffold. Before commercial deployment, the following components must be validated and completed:

- robust RTK/XMP/EXIF metadata handling for the actual camera(s), including radiometric thermal metadata;
- photogrammetric orthomosaic generation for small/medium rooftop systems;
- RGB/thermal image registration and synchronization;
- a validated PV-panel segmentation model;
- a validated defect model trained on representative German/European field data;
- calibration/quality checks and environmental acceptance criteria;
- georeferenced defect database and panel IDs;
- human review workflow;
- complete report templates and evidence chain;
- signed Windows installer and reproducible Ubuntu package;
- automated tests and test datasets.

Do not use an unvalidated AI model as the sole basis for safety-critical conclusions or insurance decisions.
