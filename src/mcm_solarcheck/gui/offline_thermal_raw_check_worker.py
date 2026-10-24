"""Owned Qt worker to inspect imported DJI M3T raw rasters without mutation."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.offline_thermal_raw_check import (
    ThermalRawCheckCancelled, check_imported_thermal_raw,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


class ThermalRawCheckThread(QThread):
    progress = Signal(int, int, int)
    result_ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, database_path, project_id, parent=None):
        super().__init__(parent)
        self._database_path = database_path
        self._project_id = project_id
        self._cancel = threading.Event()

    def request_cancel(self):
        self._cancel.set()

    def run(self):
        try:
            # Never invoke database.initialize() in the background worker.
            database = ProjectDatabase(self._database_path)
            if not database.path.is_file():
                raise ValueError("test database does not exist")
            result = check_imported_thermal_raw(
                database, self._project_id,
                on_progress=lambda done, total, issues: self.progress.emit(
                    done, total, issues,
                ),
                should_cancel=self._cancel.is_set,
            )
        except ThermalRawCheckCancelled:
            self.cancelled.emit()
        except Exception:
            # No private filenames, raw pixels, GPS coordinates or paths leak.
            self.failed.emit(
                "Thermal-Rohdatenprüfung nicht möglich. "
                "Bilddateien und Datenbank unverändert."
            )
        else:
            self.result_ready.emit(result)
