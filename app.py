from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMessageBox, QPushButton, QProgressBar, QVBoxLayout, QWidget
)

APP_NAME = "MCM-SolarCheck"


def gps_to_decimal(value, ref):
    if not value or len(value) != 3:
        return None
    def f(x):
        return float(x[0]) / float(x[1]) if hasattr(x, '__len__') else float(x)
    result = f(value[0]) + f(value[1]) / 60 + f(value[2]) / 3600
    return -result if ref in ("S", "W") else result


def read_exif(path: Path) -> dict:
    data = {"file": path.name}
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            decoded = {TAGS.get(k, k): v for k, v in exif.items()}
            gps_raw = decoded.get("GPSInfo")
            if gps_raw:
                gps = {GPSTAGS.get(k, k): v for k, v in gps_raw.items()}
                data["latitude"] = gps_to_decimal(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
                data["longitude"] = gps_to_decimal(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
            data["make"] = decoded.get("Make")
            data["model"] = decoded.get("Model")
            data["datetime"] = decoded.get("DateTimeOriginal") or decoded.get("DateTime")
    except Exception as exc:
        data["error"] = str(exc)
    return data


class SolarCheck(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} – PV-Anlagenprüfung")
        self.resize(1050, 700)
        self.project_dir: Path | None = None
        self.images: list[Path] = []

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        title = QLabel("MCM-SolarCheck")
        title.setStyleSheet("font-size: 28px; font-weight: 700; margin: 10px 0;")
        layout.addWidget(title)
        subtitle = QLabel("RGB- und Thermaldaten → Orthofoto → KI-Auswertung → Zustandsbericht")
        subtitle.setStyleSheet("color: #667085; font-size: 14px;")
        layout.addWidget(subtitle)

        row = QHBoxLayout()
        row.addWidget(QLabel("Projektname:"))
        self.project_name = QLineEdit()
        self.project_name.setPlaceholderText("z. B. PV-Anlage Musterkunde 2026")
        row.addWidget(self.project_name, 1)
        self.create_btn = QPushButton("Projekt anlegen")
        self.create_btn.clicked.connect(self.create_project)
        row.addWidget(self.create_btn)
        layout.addLayout(row)

        self.status = QLabel("Noch kein Projekt angelegt.")
        layout.addWidget(self.status)

        buttons = QHBoxLayout()
        self.import_btn = QPushButton("RTK-Fotos importieren")
        self.import_btn.clicked.connect(self.import_images)
        self.import_btn.setEnabled(False)
        buttons.addWidget(self.import_btn)
        self.analyze_btn = QPushButton("KI-Auswertung starten")
        self.analyze_btn.clicked.connect(self.run_analysis)
        self.analyze_btn.setEnabled(False)
        buttons.addWidget(self.analyze_btn)
        self.report_btn = QPushButton("Bericht erzeugen")
        self.report_btn.clicked.connect(self.create_report)
        self.report_btn.setEnabled(False)
        buttons.addWidget(self.report_btn)
        layout.addLayout(buttons)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        note = QLabel(
            "Hinweis: Automatische Befunde sind Assistenzbefunde. Die fachkundige Prüfung und "
            "die Beurteilung nach der gültigen Norm bleiben erforderlich."
        )
        note.setWordWrap(True)
        note.setStyleSheet("background:#f2f4f7; padding:10px; color:#344054;")
        layout.addWidget(note)

    def create_project(self):
        name = self.project_name.text().strip()
        if not name:
            QMessageBox.warning(self, APP_NAME, "Bitte zuerst einen Projektnamen eingeben.")
            return
        base = Path.home() / "MCM-SolarCheck" / name
        for folder in ("input", "input/rgb", "input/thermal", "orthofoto", "results", "reports", "models"):
            (base / folder).mkdir(parents=True, exist_ok=True)
        metadata = {"project": name, "created": datetime.now().isoformat(timespec="seconds"), "version": "0.1.0"}
        (base / "project.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        self.project_dir = base
        self.status.setText(f"Projekt: {base}")
        self.import_btn.setEnabled(True)
        self.report_btn.setEnabled(True)

    def import_images(self):
        if not self.project_dir:
            return
        files, _ = QFileDialog.getOpenFileNames(
            self, "RGB- und Thermalfotos auswählen", "", "Bilder (*.jpg *.jpeg *.png *.tif *.tiff);;Alle Dateien (*)"
        )
        if not files:
            return
        self.progress.setValue(0)
        for i, source in enumerate(files, 1):
            src = Path(source)
            info = read_exif(src)
            # Thermal images are kept in a separate folder when the filename suggests thermal data.
            target_dir = self.project_dir / ("input/thermal" if any(x in src.stem.lower() for x in ("thermal", "ir", "radiometric")) else "input/rgb")
            target = target_dir / src.name
            shutil.copy2(src, target)
            self.images.append(target)
            self.list.addItem(f"{src.name} | GPS: {info.get('latitude')}, {info.get('longitude')}")
            self.progress.setValue(int(i / len(files) * 100))
        self.analyze_btn.setEnabled(bool(self.images))
        self.status.setText(f"{len(self.images)} Bild(er) importiert.")

    def run_analysis(self):
        if not self.project_dir:
            return
        model = self.project_dir / "models" / "pv_defects.pt"
        if not model.exists():
            QMessageBox.information(
                self, APP_NAME,
                "Kein lokales PV-Defektmodell gefunden.\n\n"
                "Legen Sie ein geprüftes YOLO-Modell unter models/pv_defects.pt ab. "
                "Das Programm führt anschließend die Inferenz aus."
            )
            return
        try:
            from ultralytics import YOLO
            detector = YOLO(str(model))
            out = self.project_dir / "results" / "yolo"
            out.mkdir(parents=True, exist_ok=True)
            detector.predict(source=[str(p) for p in self.images], project=str(out), name="latest", save=True, save_txt=True, exist_ok=True)
            self.report_btn.setEnabled(True)
            QMessageBox.information(self, APP_NAME, "KI-Auswertung abgeschlossen. Ergebnisse liegen im Projektordner/results.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"KI-Auswertung fehlgeschlagen:\n{exc}")

    def create_report(self):
        if not self.project_dir:
            return
        report = self.project_dir / "reports" / "MCM-SolarCheck-Bericht.odt"
        try:
            from odf.opendocument import OpenDocumentText
            from odf.text import H1, H2, P
            doc = OpenDocumentText()
            doc.text.addElement(H1(text="MCM-SolarCheck – PV-Anlagen-Zustandsbericht"))
            doc.text.addElement(P(text=f"Projekt: {self.project_name.text().strip()}"))
            doc.text.addElement(P(text=f"Erstellt: {datetime.now():%d.%m.%Y %H:%M}"))
            doc.text.addElement(H2(text="1. Untersuchungsgrundlage"))
            doc.text.addElement(P(text="Auswertung georeferenzierter RGB- und Thermaldaten. Die konkrete Beurteilung ist an die gültige Ausgabe der DIN IEC/TS 62446-3 (VDE V 0126-23-3) sowie die dokumentierten Aufnahmebedingungen anzupassen."))
            doc.text.addElement(H2(text="2. Datengrundlage"))
            doc.text.addElement(P(text=f"Importierte Bilder: {len(self.images)}"))
            doc.text.addElement(H2(text="3. KI-Auswertung"))
            doc.text.addElement(P(text="Automatisch erkannte Befunde werden hier aus der Ergebnisdatenbank bzw. den YOLO-Ausgaben eingefügt. Jeder Befund muss vor Freigabe fachlich validiert werden."))
            doc.text.addElement(H2(text="4. Befundübersicht"))
            doc.text.addElement(P(text="Noch keine abschließenden Befunde eingetragen."))
            doc.text.addElement(H2(text="5. Maßnahmen / Empfehlung"))
            doc.text.addElement(P(text="Nach fachlicher Prüfung und Priorisierung der Befunde ergänzen."))
            doc.text.addElement(H2(text="6. Anlagen"))
            doc.text.addElement(P(text="Orthofoto, Thermalkarten, RGB-Bilder, Befundkarten und Detailaufnahmen."))
            doc.save(str(report))
            QMessageBox.information(self, APP_NAME, f"Bericht erstellt:\n{report}\n\nPDF kann auf Windows/Ubuntu über LibreOffice exportiert werden.")
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Berichtserstellung fehlgeschlagen:\n{exc}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = SolarCheck()
    window.show()
    sys.exit(app.exec())
