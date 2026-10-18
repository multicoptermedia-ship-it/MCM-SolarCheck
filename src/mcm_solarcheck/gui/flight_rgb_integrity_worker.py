"""Qt background worker for read-only RGB integrity scanning."""
import threading

from PySide6.QtCore import QObject, Signal, Slot

from mcm_solarcheck.services.flight_rgb_integrity_scan import (
    IntegrityScanCancelled, scan_rgb_integrity,
)


class FlightRgbIntegrityWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    completed = Signal()

    def __init__(self, source_folder, output_folder):
        super().__init__()
        self.source_folder = source_folder
        self.output_folder = output_folder
        self._stop = threading.Event()

    def request_cancel(self):
        self._stop.set()

    @Slot()
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
            self.finished.emit(result)
        finally:
            self.completed.emit()
