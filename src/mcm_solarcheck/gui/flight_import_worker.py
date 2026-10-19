"""Owned QThread running the guarded, atomic offline DJI image import."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.project_pipeline import ProjectImportCancelled


class FlightImportThread(QThread):
    progress = Signal(str, int)
    result_ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, project_service, project_id: str, source_folder: str, parent=None):
        super().__init__(parent)
        self.project_service = project_service
        self.project_id = project_id
        self.source_folder = source_folder
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        """Request cancellation without requiring a running worker Qt event loop."""
        self._cancel.set()

    def run(self) -> None:
        try:
            outcome = self.project_service.import_project_images_cancellable(
                self.project_id,
                self.source_folder,
                should_cancel=self._cancel.is_set,
                on_progress=self.progress.emit,
            )
        except ProjectImportCancelled:
            self.cancelled.emit()
        except Exception as error:
            self.failed.emit(str(error) or type(error).__name__)
        else:
            # The transaction may already have committed when a late cancel
            # is requested; report the actual persisted outcome, not a false
            # cancellation signal.
            self.result_ready.emit(outcome)
