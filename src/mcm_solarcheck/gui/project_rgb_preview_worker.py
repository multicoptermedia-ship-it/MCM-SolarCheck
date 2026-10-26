"""Owned Qt thread for an explicit offline project RGB preview; no SQL writes."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.rgb_project_preview_vertical import (
    RGBProjectPreviewCancelled,
    create_project_rgb_preview,
)


class ProjectRGBPreviewThread(QThread):
    progress = Signal(int, int, str)
    result_ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, database_path, project_id, first, second, output_dir, parent=None):
        super().__init__(parent)
        self._database_path = database_path
        self._project_id = project_id
        self._first = first
        self._second = second
        self._output_dir = output_dir
        self._cancel = threading.Event()

    def request_cancel(self):
        self._cancel.set()

    def run(self):
        try:
            result = create_project_rgb_preview(
                self._database_path,
                self._project_id, self._first, self._second,
                self._output_dir,
                should_cancel=self._cancel.is_set,
                on_progress=lambda done, total, stage: self.progress.emit(
                    done, total, stage,
                ),
            )
        except RGBProjectPreviewCancelled:
            self.cancelled.emit()
        except Exception:
            # SQLite and image decoder exceptions may contain private paths.
            self.failed.emit(
                "RGB-Projektvorschau nicht möglich. "
                "Originale und Projektdatenbank unverändert. "
                "Kein verifiziertes Orthofoto."
            )
        else:
            self.result_ready.emit(result)
