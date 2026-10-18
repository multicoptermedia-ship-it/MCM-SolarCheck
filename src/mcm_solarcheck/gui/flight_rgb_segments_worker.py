"""Background worker for local, nonmetric RGB segment exports."""
import json
import threading
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from mcm_solarcheck.services.flight_rgb_all_segments import save_all_flight_rgb_segments


class FlightRgbSegmentsWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)
    completed = Signal()

    def __init__(self, folder: str, registration_path: str, output_dir: str):
        super().__init__()
        self.folder = folder
        self.registration_path = registration_path
        self.output_dir = output_dir
        self._stop = threading.Event()

    def request_cancel(self):
        self._stop.set()

    @Slot()
    def run(self):
        try:
            with Path(self.registration_path).open(encoding="utf-8") as stream:
                registration = json.load(stream)
            result = save_all_flight_rgb_segments(
                self.folder, registration, self.output_dir,
                on_progress=lambda done, total, record: self.progress.emit(
                    done, total, record["status"]
                ),
                should_cancel=self._stop.is_set,
            )
        except (ValueError, OSError, KeyError, TypeError) as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(result)
        finally:
            self.completed.emit()
