# MCM-SolarCheck – Installation

## Windows 10 Home

1. Install Python 3.11 (64-bit) from the official Python website and activate **Add Python to PATH** during setup.
2. Download/clone this repository.
3. Open PowerShell in the repository folder.
4. Create the virtual environment:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5. Start the program:

```powershell
python app.py
```

If PowerShell blocks activation, use:

```powershell
.\.venv\Scripts\python.exe app.py
```

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
