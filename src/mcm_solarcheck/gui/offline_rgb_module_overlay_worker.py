"""Owned cancellable Qt worker for one private, read-only module overlay."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.offline_module_sample import ModuleSampleCancelled
from mcm_solarcheck.services.offline_rgb_module_overlay import (
    render_imported_rgb_module_overlay,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


class RgbModuleOverlayThread(QThread):
    result_ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, database_path, project_id, sample_index, parent=None):
        super().__init__(parent)
        self._database_path = database_path
        self._project_id = project_id
        self._sample_index = sample_index
        self._cancel = threading.Event()

    def request_cancel(self):
        self._cancel.set()

    def run(self):
        try:
            db = ProjectDatabase(self._database_path)
            if not db.path.is_file():
                raise ValueError("isolated database missing")
            result = render_imported_rgb_module_overlay(
                db, self._project_id, sample_index=self._sample_index,
                should_cancel=self._cancel.is_set,
            )
        except ModuleSampleCancelled:
            self.cancelled.emit()
        except Exception:
            # Never disclose sensitive customer paths, image bytes or filenames.
            self.failed.emit(
                "RGB-Modulvorschau nicht möglich. "
                "Bilddateien, Module und Projektdaten unverändert."
            )
        else:
            self.result_ready.emit(result)
