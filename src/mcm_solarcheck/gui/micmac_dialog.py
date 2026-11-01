"""Explicit user-started local MicMac job, with an owned cancellable worker."""
from __future__ import annotations

import threading

from PySide6.QtCore import QSettings, QThread, Qt, Signal
from PySide6.QtWidgets import QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from mcm_solarcheck.services.micmac_orthophotos import (
    MicMacCancelled, MicMacError, generate_micmac_orthophotos,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


class MicMacThread(QThread):
    progress = Signal(str)
    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, database_path, project_id, executable, output_parent, crs, parent=None):
        super().__init__(parent)
        self._args = database_path, project_id, executable, output_parent, crs
        self.cancel_event = threading.Event()

    def request_cancel(self):
        self.cancel_event.set()

    def run(self):
        database, project, executable, output, crs = self._args
        try:
            result = generate_micmac_orthophotos(
                ProjectDatabase(database), project, executable, output,
                target_crs=crs or None, should_cancel=self.cancel_event.is_set,
                on_progress=self.progress.emit,
            )
        except MicMacCancelled:
            pass
        except MicMacError as error:
            self.failed.emit(str(error))
        except Exception:
            self.failed.emit(
                "Lokale MicMac-Erzeugung fehlgeschlagen. Private Protokolle im "
                "Ausgabeordner prüfen. Originale und Projektfreigaben unverändert."
            )
        else:
            self.result_ready.emit(result)


class MicMacDialog(QDialog):
    completed = Signal(object)

    def __init__(self, database_path, project_id, parent=None, *, settings=None):
        super().__init__(parent)
        self.setWindowTitle("RGB- und Thermal-Orthofotos mit MicMac erstellen")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._database_path = database_path
        self._project_id = project_id
        self._settings = settings if settings is not None else QSettings("MCM", "SolarCheck")
        self._thread = None
        self._closing = False
        self._result = None
        layout = QVBoxLayout(self)
        description = QLabel(
            "MicMac verarbeitet Arbeitskopien der importierten RGB- und Thermalbilder "
            "lokal. Kamerapositionen werden aus dem Projekt übernommen. "
            "Beide GeoTIFFs werden anschließend im Projekt gespeichert. "
            "Thermal dient zunächst der Darstellung; keine bestätigten Celsiuswerte.", self,
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addWidget(QLabel("Separat installiertes MicMac-Programm", self))
        self.executable = QLineEdit(str(self._settings.value("micmac/executable", "")), self)
        self.executable.setObjectName("micmac_executable")
        pick_exe = QPushButton("mm3d auswählen …", self)
        pick_exe.clicked.connect(self._choose_executable)
        row = QHBoxLayout()
        row.addWidget(self.executable, 1)
        row.addWidget(pick_exe)
        layout.addLayout(row)
        layout.addWidget(QLabel("Privater Ausgabeordner, getrennt von Originalen und Git", self))
        self.output = QLineEdit(self)
        self.output.setObjectName("micmac_output_parent")
        pick_output = QPushButton("Ordner auswählen …", self)
        pick_output.clicked.connect(self._choose_output)
        row = QHBoxLayout()
        row.addWidget(self.output, 1)
        row.addWidget(pick_output)
        layout.addLayout(row)
        layout.addWidget(QLabel("Ziel-Koordinatensystem (optional)", self))
        self.crs = QLineEdit(self)
        self.crs.setObjectName("micmac_target_crs")
        self.crs.setPlaceholderText("Leer: passende WGS84-UTM-Zone aus importierten Kamerapositionen")
        layout.addWidget(self.crs)
        self.status = QLabel("Bereit. Start erfolgt erst über „Lokal erstellen“.", self)
        self.status.setObjectName("micmac_job_status")
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.start_button = QPushButton("Lokal erstellen", self)
        self.start_button.setObjectName("micmac_start")
        self.start_button.clicked.connect(self._start)
        self.cancel_button = QPushButton("Schließen", self)
        self.cancel_button.setObjectName("micmac_cancel")
        self.cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.start_button)
        buttons.addWidget(self.cancel_button)
        layout.addLayout(buttons)
        self._inputs = (self.executable, self.output, self.crs, pick_exe, pick_output)
        self.resize(690, 360)

    @property
    def running(self):
        return self._thread is not None

    def _choose_executable(self):
        path, _ = QFileDialog.getOpenFileName(self, "MicMac auswählen", self.executable.text(), "MicMac (mm3d.exe mm3d)")
        if path:
            self.executable.setText(path)

    def _choose_output(self):
        path = QFileDialog.getExistingDirectory(self, "Privaten Ausgabeordner auswählen")
        if path:
            self.output.setText(path)

    def _start(self):
        if self._thread is not None:
            return
        if not self.executable.text().strip() or not self.output.text().strip():
            self.status.setText("Bitte MicMac-Programm und privaten Ausgabeordner auswählen.")
            return
        self._settings.setValue("micmac/executable", self.executable.text().strip())
        self._closing = False
        self._result = None
        thread = MicMacThread(
            self._database_path, self._project_id, self.executable.text().strip(),
            self.output.text().strip(), self.crs.text().strip(), self,
        )
        self._thread = thread
        thread.progress.connect(self._progress)
        thread.failed.connect(self._progress)
        thread.result_ready.connect(self._remember_result)
        thread.finished.connect(self._finished)
        for widget in self._inputs:
            widget.setEnabled(False)
        self.start_button.setEnabled(False)
        self.cancel_button.setText("Abbrechen")
        self.status.setText("Lokale MicMac-Erzeugung startet …")
        thread.start()

    def _progress(self, text):
        if not self._closing:
            self.status.setText(text)

    def _remember_result(self, result):
        self._result = result

    def _finished(self):
        thread = self._thread
        if thread is None:
            return
        thread.wait()
        cancelled = thread.cancel_event.is_set()
        self._thread = None
        thread.deleteLater()
        if self._closing or cancelled:
            super().reject()
            return
        if self._result is not None:
            self.completed.emit(self._result)
            super().accept()
            return
        for widget in self._inputs:
            widget.setEnabled(True)
        self.start_button.setEnabled(True)
        self.cancel_button.setText("Schließen")

    def reject(self):
        if self._thread is not None:
            self._closing = True
            self._thread.request_cancel()
            self.status.setText("Abbruch wird abgeschlossen; Ergebnis wird nicht übernommen …")
            self.cancel_button.setEnabled(False)
        else:
            super().reject()

    def closeEvent(self, event):
        if self._thread is not None:
            self.reject()
            event.ignore()
        else:
            super().closeEvent(event)
