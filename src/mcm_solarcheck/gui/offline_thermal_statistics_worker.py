"""Owned Qt worker for read-only per-frame raw SENSOR statistics.

Neither decoded pixels nor customer paths leave the worker; only aggregate
results are emitted. A completed pre-analysis never releases expert review.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.offline_thermal_raw_check import ThermalRawCheckCancelled
from mcm_solarcheck.services.offline_thermal_statistics import (
    analyze_imported_thermal_sensor_values,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


class ThermalStatisticsThread(QThread):
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
            database = ProjectDatabase(self._database_path)
            # Never initialize/migrate the inspection database in a worker.
            if not database.path.is_file():
                raise ValueError("test database does not exist")
            result = analyze_imported_thermal_sensor_values(
                database, self._project_id,
                on_progress=lambda done, total, issues: self.progress.emit(
                    done, total, issues,
                ),
                should_cancel=self._cancel.is_set,
            )
        except ThermalRawCheckCancelled:
            self.cancelled.emit()
        except Exception:
            # Never expose file paths, parsing internals or sensitive readings.
            self.failed.emit(
                "Thermalstatistik nicht möglich. "
                "Bilddateien und Datenbank unverändert."
            )
        else:
            self.result_ready.emit(result)
