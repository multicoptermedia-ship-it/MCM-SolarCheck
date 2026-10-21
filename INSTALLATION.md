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
