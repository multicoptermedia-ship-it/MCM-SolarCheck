"""SQLite persistence for MCM-SolarCheck inspection projects."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import json
import sqlite3
from typing import Iterator

from mcm_solarcheck.domain.models import Finding, ImageFrame, ImagePair, PVModule, ThermalFrame

SCHEMA_VERSION = 2

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_info (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS image_frames (
 frame_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
 source_file TEXT NOT NULL, timestamp_utc TEXT, camera_make TEXT, camera_model TEXT, width INTEGER, height INTEGER,
 latitude REAL, longitude REAL, altitude_m REAL, metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS thermal_frames (
 frame_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
 source_file TEXT NOT NULL, timestamp_utc TEXT, camera_make TEXT, camera_model TEXT, width INTEGER, height INTEGER,
 latitude REAL, longitude REAL, altitude_m REAL, rtk_status TEXT, rtk_std_lat_m REAL, rtk_std_lon_m REAL,
 rtk_std_height_m REAL, rtk_correction_age_s REAL, rtk_altitude_type TEXT, thermal_source TEXT NOT NULL,
 quality_grade TEXT, raw_min INTEGER, raw_max INTEGER, raw_mean REAL, raw_median REAL, raw_p95 REAL, raw_p99 REAL,
 metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS image_pairs (
 pair_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
 rgb_frame_id TEXT NOT NULL REFERENCES image_frames(frame_id) ON DELETE CASCADE,
 thermal_frame_id TEXT NOT NULL REFERENCES thermal_frames(frame_id) ON DELETE CASCADE,
 confidence REAL NOT NULL, method TEXT NOT NULL, distance_m REAL, time_delta_s REAL);
CREATE TABLE IF NOT EXISTS pv_modules (
 module_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
 frame_id TEXT NOT NULL, polygon_json TEXT NOT NULL, detection_confidence REAL, detector TEXT NOT NULL,
 latitude REAL, longitude REAL, altitude_m REAL, metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS findings (
 finding_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
 thermal_frame_id TEXT NOT NULL REFERENCES thermal_frames(frame_id) ON DELETE CASCADE,
 pixel_x INTEGER NOT NULL, pixel_y INTEGER NOT NULL, finding_type TEXT NOT NULL, confidence REAL, raw_value INTEGER,
 raw_delta_from_median REAL, temperature_c REAL, module_id TEXT, latitude REAL, longitude REAL, altitude_m REAL,
 reviewer_status TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}');
CREATE INDEX IF NOT EXISTS idx_rgb_project ON image_frames(project_id);
CREATE INDEX IF NOT EXISTS idx_frames_project ON thermal_frames(project_id);
CREATE INDEX IF NOT EXISTS idx_pairs_project ON image_pairs(project_id);
CREATE INDEX IF NOT EXISTS idx_modules_project ON pv_modules(project_id);
CREATE INDEX IF NOT EXISTS idx_findings_project ON findings(project_id);
CREATE INDEX IF NOT EXISTS idx_findings_frame ON findings(thermal_frame_id);
"""


class ProjectDatabase:
    def __init__(self, path: str | Path) -> None: self.path = Path(path)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True); db = sqlite3.connect(self.path); db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA foreign_keys = ON"); yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(_SCHEMA); row = db.execute("SELECT version FROM schema_info LIMIT 1").fetchone()
            if row is None: db.execute("INSERT INTO schema_info(version) VALUES (?)", (SCHEMA_VERSION,))
            elif row["version"] != SCHEMA_VERSION: raise RuntimeError(f"Unsupported database schema version: {row['version']}; migration required")

    def create_project(self, project_id: str, name: str) -> None:
        with self.connect() as db: db.execute("INSERT OR REPLACE INTO projects(project_id,name) VALUES (?,?)", (project_id,name))

    def save_image_frames(self, project_id: str, frames: tuple[ImageFrame, ...]) -> None:
        with self.connect() as db:
            db.executemany("INSERT OR REPLACE INTO image_frames VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", [
                (f.frame_id, project_id, str(f.source_file), f.timestamp_utc.isoformat() if f.timestamp_utc else None,
                 f.camera_make, f.camera_model, f.width, f.height, f.position.latitude if f.position else None,
                 f.position.longitude if f.position else None, f.position.altitude_m if f.position else None,
                 json.dumps(f.metadata, ensure_ascii=False)) for f in frames])

    def save_thermal_frame(self, project_id: str, frame: ThermalFrame, quality) -> None:
        s=quality.statistics; p=frame.position
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO thermal_frames VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (frame.frame_id,project_id,str(frame.source_file),frame.timestamp_utc.isoformat() if frame.timestamp_utc else None,
                 frame.camera_make,frame.camera_model,frame.thermal_width,frame.thermal_height,p.latitude if p else None,p.longitude if p else None,
                 p.altitude_m if p else None,frame.rtk.status,frame.rtk.std_lat_m,frame.rtk.std_lon_m,frame.rtk.std_height_m,
                 frame.rtk.correction_age_s,frame.rtk.altitude_type,frame.thermal_source,quality.grade.value,s.minimum,s.maximum,s.mean,s.median,s.p95,s.p99,
                 json.dumps(frame.metadata,ensure_ascii=False)))

    def save_pairs(self, project_id: str, pairs: tuple[ImagePair, ...]) -> None:
        with self.connect() as db: db.executemany("INSERT OR REPLACE INTO image_pairs VALUES (?,?,?,?,?,?,?,?)", [
            (p.pair_id,project_id,p.rgb_frame_id,p.thermal_frame_id,p.confidence,p.method,p.distance_m,p.time_delta_s) for p in pairs])

    def save_modules(self, project_id: str, modules: tuple[PVModule, ...]) -> None:
        with self.connect() as db: db.executemany("INSERT OR REPLACE INTO pv_modules VALUES (?,?,?,?,?,?,?,?,?,?,?)", [
            (m.module_id,project_id,m.frame_id,json.dumps(m.polygon_px),m.detection_confidence,m.detector,
             m.position.latitude if m.position else None,m.position.longitude if m.position else None,m.position.altitude_m if m.position else None,
             json.dumps(m.metadata,ensure_ascii=False), None) for m in modules])

    def save_findings(self, project_id: str, findings: tuple[Finding, ...]) -> None:
        with self.connect() as db: db.executemany("INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [
            (f.finding_id,project_id,f.thermal_frame_id,f.pixel_x,f.pixel_y,f.finding_type,f.confidence,f.raw_value,f.raw_delta_from_median,
             f.temperature_c,f.module_id,f.position.latitude if f.position else None,f.position.longitude if f.position else None,
             f.position.altitude_m if f.position else None,f.reviewer_status,json.dumps(f.metadata,ensure_ascii=False)) for f in findings])
