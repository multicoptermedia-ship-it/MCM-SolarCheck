"""Owned QThread for non-destructive, large DJI folder preflight."""
from __future__ import annotations

import threading

from PySide6.QtCore import QThread, Signal

from mcm_solarcheck.services.flight_preflight import (
    FlightPreflightCancelled,
    FlightPreflightResult,
    scan_dji_flight_preflight,
)


def format_flight_preflight(result: FlightPreflightResult) -> str:
    """Present observed file metadata, not image validation or flight coverage."""
    issues = (
        " Hinweise (max. 8): " + " | ".join(result.issue_examples)
        if result.issue_examples else ""
    )
    return (
        f"DJI-Ordner-Vorprüfung abgeschlossen (nur Dateinamen und Größen): "
        f"{result.entries_seen} Einträge, {result.rgb_files} RGB-Dateien "
        f"({result.rgb_bytes} Bytes), {result.thermal_files} Thermaldateien "
        f"({result.thermal_bytes} Bytes). "
        f"Leere Bilddateien: {result.empty_images}; "
        f"symbolische Links: {result.symlinks}; "
        f"sonstige Einträge: {result.other_entries}; "
        f"nicht lesbare Einträge: {result.inaccessible_entries}. "
        "Keine Pixeldekodierung, keine Paarkontrolle, keine Temperatur- "
        "oder Geo-Validierung und keine Änderung von Originalbildern."
        + issues
    )


class FlightPreflightThread(QThread):
    progress = Signal(int)
    result_ready = Signal(object)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, source_folder: str, parent=None):
        super().__init__(parent)
        self.source_folder = source_folder
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        try:
            result = scan_dji_flight_preflight(
                self.source_folder,
                on_progress=self.progress.emit,
                should_cancel=self._cancel.is_set,
            )
        except FlightPreflightCancelled:
            self.cancelled.emit()
        except (OSError, ValueError) as exc:
            self.failed.emit(str(exc))
        else:
            self.result_ready.emit(result)
