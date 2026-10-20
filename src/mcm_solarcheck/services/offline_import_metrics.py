"""Anonymous per-import runtime observations for offline DJI desktop workflows.

This module does not read images, track file names, or upload telemetry.
A process-wide RSS high-water mark is *not* an isolated import peak. A fresh
application process is required to interpret it as a meaningful upper bound.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time
from typing import Callable


_PHASES = {
    "Einlesen und Zuordnen": "read_and_pair",
    "Atomare SQLite-Speicherung": "sqlite_commit",
}
_OUTCOMES = frozenset(("succeeded", "failed", "cancelled"))


def process_peak_rss_bytes() -> int | None:
    """Best-effort process-lifetime maximum; unavailable means *unknown*."""
    try:
        if sys.platform == "win32":
            # Optional, not a runtime dependency; no invented Windows value.
            import psutil
            value = psutil.Process().memory_info().peak_wset
        else:
            import resource
            value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform != "darwin":
                value *= 1024
        if type(value) is not int or value <= 0:
            return None
        return value
    except (ImportError, OSError, AttributeError, ValueError):
        return None


@dataclass(frozen=True)
class ImportPerformanceSnapshot:
    elapsed_seconds: float
    read_and_pair_seconds: float | None
    sqlite_commit_seconds: float | None
    observed_progress_updates: int
    reported_checkpoints: int
    process_peak_rss_bytes: int | None
    process_peak_rss_at_start_bytes: int | None
    outcome: str

    def __post_init__(self):
        if self.outcome not in _OUTCOMES:
            raise ValueError("invalid import outcome")
        for name in (
            "elapsed_seconds", "read_and_pair_seconds", "sqlite_commit_seconds",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, (int, float)) or value < 0):
                raise ValueError("invalid import duration")
        if type(self.observed_progress_updates) is not int or self.observed_progress_updates < 0:
            raise ValueError("invalid progress count")
        if type(self.reported_checkpoints) is not int or self.reported_checkpoints < 0:
            raise ValueError("invalid checkpoint count")

    def anonymous_report(self) -> dict:
        """Allowlist only measurement fields: never paths, projects, or images."""
        return {
            "schema_version": 1,
            "measurement": "offline_dji_import_process_observation",
            "outcome": self.outcome,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "read_and_pair_seconds": (
                round(self.read_and_pair_seconds, 3)
                if self.read_and_pair_seconds is not None else None
            ),
            "sqlite_commit_seconds": (
                round(self.sqlite_commit_seconds, 3)
                if self.sqlite_commit_seconds is not None else None
            ),
            "progress_updates": self.observed_progress_updates,
            "checkpoints_reported": self.reported_checkpoints,
            "process_peak_rss_bytes": self.process_peak_rss_bytes,
            "process_peak_rss_at_start_bytes": self.process_peak_rss_at_start_bytes,
            "rss_scope": "entire_process_lifetime_not_isolated_import",
            "sampling": "phase_changes_and_coarse_progress_only",
            "contains_source_paths": False,
            "contains_project_or_customer_ids": False,
            "is_real_dji_validation": False,
        }


class ImportPerformanceProbe:
    """Bounded observation of stage time and peak process RSS.

    No arbitrary phase labels or messages are retained; callbacks are sampled
    on the worker thread and measurements remain explicitly best-effort.
    """

    def __init__(
        self, *,
        clock_ns: Callable[[], int] = time.perf_counter_ns,
        peak_rss: Callable[[], int | None] = process_peak_rss_bytes,
    ):
        self._clock = clock_ns
        self._peak_rss = peak_rss
        self._started = clock_ns()
        self._rss_start = peak_rss()
        self._rss_peak = self._rss_start
        self._phase = None
        self._phase_started = None
        self._durations = {}
        self._updates = 0
        self._checkpoints = 0
        self._finished = False

    def observe(self, phase: str, count: int) -> None:
        if self._finished:
            raise RuntimeError("import measurement already finalized")
        now = self._clock()
        normalized = _PHASES.get(phase)
        if normalized != self._phase:
            self._close_phase(now)
            self._phase = normalized
            self._phase_started = now if normalized is not None else None
        self._updates += 1
        if type(count) is int and count >= 0:
            self._checkpoints = max(self._checkpoints, count)
        self._sample_rss()

    def _sample_rss(self) -> None:
        current = self._peak_rss()
        if current is not None:
            self._rss_peak = (
                current if self._rss_peak is None
                else max(self._rss_peak, current)
            )

    def _close_phase(self, now: int) -> None:
        if self._phase is not None and self._phase_started is not None:
            duration = max(0, now - self._phase_started) / 1e9
            self._durations[self._phase] = (
                self._durations.get(self._phase, 0.0) + duration
            )

    def finish(self, outcome: str) -> ImportPerformanceSnapshot:
        if self._finished:
            raise RuntimeError("import measurement already finalized")
        if outcome not in _OUTCOMES:
            raise ValueError("invalid import outcome")
        now = self._clock()
        self._close_phase(now)
        self._sample_rss()
        self._finished = True
        return ImportPerformanceSnapshot(
            elapsed_seconds=max(0, now - self._started) / 1e9,
            read_and_pair_seconds=self._durations.get("read_and_pair"),
            sqlite_commit_seconds=self._durations.get("sqlite_commit"),
            observed_progress_updates=self._updates,
            reported_checkpoints=self._checkpoints,
            process_peak_rss_bytes=self._rss_peak,
            process_peak_rss_at_start_bytes=self._rss_start,
            outcome=outcome,
        )


def format_import_performance(snapshot: ImportPerformanceSnapshot) -> str:
    """Plain-text UI summary with an explicit measurement scope."""
    rss = (
        f"{snapshot.process_peak_rss_bytes / (1024 * 1024):.1f} MiB"
        if snapshot.process_peak_rss_bytes is not None
        else "nicht verfügbar"
    )
    phase = (
        f"Einlesen/Zuordnen: {snapshot.read_and_pair_seconds:.1f} s; "
        if snapshot.read_and_pair_seconds is not None else ""
    )
    save = (
        f"SQLite: {snapshot.sqlite_commit_seconds:.1f} s; "
        if snapshot.sqlite_commit_seconds is not None else ""
    )
    return (
        f"Import-Messung ({snapshot.outcome}): "
        f"{snapshot.elapsed_seconds:.1f} s insgesamt; {phase}{save}"
        f"Prozess-RSS-Höchstwert seit Programmstart: {rss}. "
        "Dies ist keine isolierte Importspitze oder garantierte RAM-Obergrenze. "
        "Keine Bildinhalte oder personenbezogenen Angaben werden gespeichert."
    )


def save_anonymous_import_report(
    snapshot: ImportPerformanceSnapshot, destination: str | Path,
) -> Path:
    """Opt-in local JSON report, exclusively created without overwriting."""
    target = Path(destination)
    if target.suffix.lower() != ".json":
        raise ValueError("diagnostic report must be a JSON file")
    if not target.is_absolute():
        raise ValueError("diagnostic report needs an absolute local path")
    if not target.parent.is_dir():
        raise ValueError("diagnostic target directory does not exist")
    if any(part.is_symlink() for part in (target.parent, *target.parent.parents)):
        raise ValueError("diagnostic destination cannot traverse symlinks")
    # 'xb' is atomic with respect to an already existing destination.
    content = json.dumps(
        snapshot.anonymous_report(), ensure_ascii=False, indent=2,
    ).encode("utf-8")
    created = False
    try:
        with target.open("xb") as stream:
            created = True
            stream.write(content)
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise
    return target
