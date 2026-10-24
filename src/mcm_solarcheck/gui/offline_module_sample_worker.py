"""Owned Qt thread for authenticated, bounded RGB PV proposal diagnostics."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.offline_module_sample import (
    ModuleSampleCancelled, sample_imported_rgb_module_evidence,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


class ModuleSampleThread(QThread):
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
            if not database.path.is_file():
                raise ValueError("isolated database missing")
            result = sample_imported_rgb_module_evidence(
                database, self._project_id,
                should_cancel=self._cancel.is_set,
                on_progress=lambda done, total, errors: self.progress.emit(
                    done, total, errors,
                ),
            )
        except ModuleSampleCancelled:
            self.cancelled.emit()
        except Exception:
            # Fail closed without showing customer paths, GPS or pixels.
            self.failed.emit(
                "RGB-Erkennungsstichprobe nicht möglich. "
                "Bilddateien und Datenbank unverändert."
            )
        else:
            self.result_ready.emit(result)
