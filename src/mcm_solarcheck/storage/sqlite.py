"""SQLite persistence for MCM-SolarCheck projects and thermal findings."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
from typing import Iterator

from mcm_solarcheck.domain.models import Finding, ThermalFrame

SCHEMA_VERSION = 1

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_info (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS thermal_frames (
    frame_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    source_file TEXT NOT NULL,
    timestamp_utc TEXT,
    camera_make TEXT,
    camera_model TEXT,
    width INTEGER,
    height INTEGER,
    latitude REAL,
    longitude REAL,
    altitude_m REAL,
    rtk_status TEXT,
    rtk_std_lat_m REAL,
    rtk_std_lon_m REAL,
    rtk_std_height_m REAL,
    rtk_correction_age_s REAL,
    rtk_altitude_type TEXT,
    thermal_source TEXT NOT NULL,
    quality_grade TEXT,
    raw_min INTEGER,
    raw_max INTEGER,
    raw_mean REAL,
    raw_median REAL,
    raw_p95 REAL,
    raw_p99 REAL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS findings (
    finding_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    thermal_frame_id TEXT NOT NULL REFERENCES thermal_frames(frame_id) ON DELETE CASCADE,
    pixel_x INTEGER NOT NULL,
    pixel_y INTEGER NOT NULL,
    finding_type TEXT NOT NULL,
    confidence REAL,
    raw_value INTEGER,
    raw_delta_from_median REAL,
    temperature_c REAL,
    module_id TEXT,
    latitude REAL,
    longitude REAL,
    altitude_m REAL,
    reviewer_status TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_frames_project ON thermal_frames(project_id);
CREATE INDEX IF NOT EXISTS idx_findings_project ON findings(project_id);
CREATE INDEX IF NOT EXISTS idx_findings_frame ON findings(thermal_frame_id);
"""


class ProjectDatabase:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(_SCHEMA)
            row = db.execute("SELECT version FROM schema_info LIMIT 1").fetchone()
            if row is None:
                db.execute("INSERT INTO schema_info(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION:
                raise RuntimeError(f"Unsupported database schema version: {row['version']}")

    def create_project(self, project_id: str, name: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO projects(project_id, name) VALUES (?, ?)",
                (project_id, name),
            )

    def save_thermal_frame(self, project_id: str, frame: ThermalFrame, quality) -> None:
        stats = quality.statistics
        pos = frame.position
        with self.connect() as db:
            db.execute(
                """INSERT OR REPLACE INTO thermal_frames(
                frame_id, project_id, source_file, timestamp_utc, camera_make, camera_model,
                width, height, latitude, longitude, altitude_m, rtk_status, rtk_std_lat_m,
                rtk_std_lon_m, rtk_std_height_m, rtk_correction_age_s, rtk_altitude_type,
                thermal_source, quality_grade, raw_min, raw_max, raw_mean, raw_median,
                raw_p95, raw_p99, metadata_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (frame.frame_id, project_id, str(frame.source_file),
                 frame.timestamp_utc.isoformat() if frame.timestamp_utc else None,
                 frame.camera_make, frame.camera_model, frame.thermal_width, frame.thermal_height,
                 pos.latitude if pos else None, pos.longitude if pos else None,
                 pos.altitude_m if pos else None, frame.rtk.status, frame.rtk.std_lat_m,
                 frame.rtk.std_lon_m, frame.rtk.std_height_m, frame.rtk.correction_age_s,
                 frame.rtk.altitude_type, frame.thermal_source, quality.grade.value,
                 stats.minimum, stats.maximum, stats.mean, stats.median, stats.p95, stats.p99,
                 json.dumps(frame.metadata, ensure_ascii=False)),
            )

    def save_findings(self, project_id: str, findings: tuple[Finding, ...]) -> None:
        with self.connect() as db:
            db.executemany(
                """INSERT OR REPLACE INTO findings(
                finding_id, project_id, thermal_frame_id, pixel_x, pixel_y, finding_type,
                confidence, raw_value, raw_delta_from_median, temperature_c, module_id,
                latitude, longitude, altitude_m, reviewer_status, metadata_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(
                    f.finding_id, project_id, f.thermal_frame_id, f.pixel_x, f.pixel_y,
                    f.finding_type, f.confidence, f.raw_value, f.raw_delta_from_median,
                    f.temperature_c, f.module_id,
                    f.position.latitude if f.position else None,
                    f.position.longitude if f.position else None,
                    f.position.altitude_m if f.position else None,
                    f.reviewer_status, json.dumps(f.metadata, ensure_ascii=False),
                ) for f in findings],
            )
