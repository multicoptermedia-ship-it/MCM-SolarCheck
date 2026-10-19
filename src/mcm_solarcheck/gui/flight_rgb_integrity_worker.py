"""Cancellable Qt thread for read-only local RGB working-array integrity scans.

The QThread object remains owned by the GUI thread. Only run() executes in the
background; the shared service has no Qt widget dependencies.
"""
import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.flight_rgb_integrity_scan import (
    IntegrityScanCancelled, scan_rgb_integrity,
)


class FlightRgbIntegrityThread(QThread):
    progress = Signal(int, int, str)
    result_ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, source_folder, output_folder, parent=None):
        super().__init__(parent)
        self.source_folder = source_folder
        self.output_folder = output_folder
        self._stop = threading.Event()

    def request_cancel(self):
        """Signal cancellation without relying on a blocked Qt event loop."""
        self._stop.set()

    def run(self):
        try:
            result = scan_rgb_integrity(
                self.source_folder, self.output_folder,
                on_progress=lambda done, total, status: self.progress.emit(
                    done, total, status),
                should_cancel=self._stop.is_set,
            )
        except IntegrityScanCancelled:
            self.cancelled.emit()
        except (ValueError, OSError, TypeError) as exc:
            self.failed.emit(str(exc))
        else:
            self.result_ready.emit(result)
