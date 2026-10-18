"""Qt worker for complete-flight RGB checks; never touch widgets from worker thread."""
from PySide6.QtCore import QObject, Signal, Slot

from mcm_solarcheck.services.flight_rgb_link_run import (
    FlightRunCancelled, save_flight_rgb_link_run,
)


class FlightRgbWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    completed = Signal()

    def __init__(self, directory: str, destination: str):
        super().__init__()
        self.directory = directory
        self.destination = destination
        import threading
        self._stop = threading.Event()

    def request_cancel(self):
        """Thread-safe; may be called directly by the GUI while run() is busy."""
        self._stop.set()

    @Slot()
    def run(self):
        try:
            result = save_flight_rgb_link_run(
                self.directory, self.destination,
                on_progress=lambda done, total, record: self.progress.emit(
                    done, total, record["status"]
                ),
                should_cancel=self._stop.is_set,
            )
        except FlightRunCancelled:
            self.cancelled.emit()
        except (ValueError, OSError, RuntimeError) as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)
        finally:
            self.completed.emit()
