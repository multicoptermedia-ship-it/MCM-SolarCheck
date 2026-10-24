"""Owned Qt background thread for read-only imported-image checks.

The worker opens its own SQLite connection, never a GUI connection. Only
bounded counts cross Qt signals: no customer filenames, paths or GPS data.
"""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.offline_imported_image_check import (
    ImportedImageCheckCancelled, check_imported_image_originals,
)
from mcm_solarcheck.storage.sqlite import ProjectDatabase


class ImportedImageCheckThread(QThread):
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
        """Cooperative cancellation also during chunked hashing."""
        self._cancel.set()

    def run(self):
        try:
            # Only inspect an already-existing SQLite project. initialize()
            # is intentionally omitted to prevent migrations in this thread.
            database = ProjectDatabase(self._database_path)
            if not database.path.is_file():
                raise ValueError("test database does not exist")
            result = check_imported_image_originals(
                database, self._project_id,
                on_progress=lambda done, total, issues: self.progress.emit(
                    done, total, issues,
                ),
                should_cancel=self._cancel.is_set,
            )
        except ImportedImageCheckCancelled:
            self.cancelled.emit()
        except Exception:
            # Any dependency/parser/SQL error may carry private paths.
            self.failed.emit(
                "Dateiprüfung nicht möglich. Originale und Datenbank unverändert."
            )
        else:
            self.result_ready.emit(result)
