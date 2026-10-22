"""Owned QThread running the guarded, atomic offline DJI image import."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.project_pipeline import ProjectImportCancelled
from mcm_solarcheck.services.offline_import_metrics import ImportPerformanceProbe


class FlightImportThread(QThread):
    progress = Signal(str, int)
    result_ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    metrics_ready = Signal(object)

    def __init__(self, project_service, project_id: str, source_folder: str, parent=None,
                 *, original_zips=None, original_files=None, include_unpaired_thermal=False):
        super().__init__(parent)
        self.project_service = project_service
        self.project_id = project_id
        self.source_folder = source_folder
        if original_zips is not None and original_files is not None:
            raise ValueError('Choose loose originals or ZIP archives, not both')
        self.original_zips = original_zips
        self.original_files = original_files
        self.include_unpaired_thermal = include_unpaired_thermal
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        """Request cancellation without requiring a running worker Qt event loop."""
        self._cancel.set()

    def run(self) -> None:
        probe = ImportPerformanceProbe()

        def on_progress(phase: str, count: int) -> None:
            probe.observe(phase, count)
            self.progress.emit(phase, count)

        try:
            if self.original_files is not None:
                outcome = self.project_service.import_project_original_files_cancellable(
                    self.project_id, self.original_files,
                    should_cancel=self._cancel.is_set,
                    on_progress=on_progress,
                )
            elif self.original_zips is not None:
                outcome = self.project_service.import_project_original_zips_cancellable(
                    self.project_id,
                    self.original_zips[0],
                    self.original_zips[1],
                    include_unpaired_thermal=self.include_unpaired_thermal,
                    should_cancel=self._cancel.is_set,
                    on_progress=on_progress,
                )
            else:
                outcome = self.project_service.import_project_images_cancellable(
                    self.project_id,
                    self.source_folder,
                    should_cancel=self._cancel.is_set,
                    on_progress=on_progress,
                )
        except ProjectImportCancelled:
            self.metrics_ready.emit(probe.finish("cancelled"))
            self.cancelled.emit()
        except Exception as error:
            self.metrics_ready.emit(probe.finish("failed"))
            self.failed.emit(str(error) or type(error).__name__)
        else:
            # Report real persistence outcome even when cancellation was
            # requested after the SQLite transaction committed.
            attempt, _import_data, state = outcome
            outcome_kind = "succeeded" if attempt.succeeded else "failed"
            self.metrics_ready.emit(probe.finish(outcome_kind))
            # Keep the large batch out of queued signals to the main thread.
            self.result_ready.emit((attempt, None, state))
