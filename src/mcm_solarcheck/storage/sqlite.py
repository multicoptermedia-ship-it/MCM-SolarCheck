"""SQLite persistence for MCM-SolarCheck inspection projects."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json, sqlite3
from typing import Iterator
from mcm_solarcheck.domain.models import Finding, ImageFrame, ImagePair, PVModule, ThermalFrame

SCHEMA_VERSION = 4
_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_info(version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS image_frames(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,frame_id TEXT NOT NULL,source_file TEXT NOT NULL,timestamp_utc TEXT,camera_make TEXT,camera_model TEXT,width INTEGER,height INTEGER,latitude REAL,longitude REAL,altitude_m REAL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,frame_id));
CREATE TABLE IF NOT EXISTS thermal_frames(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,frame_id TEXT NOT NULL,source_file TEXT NOT NULL,timestamp_utc TEXT,camera_make TEXT,camera_model TEXT,width INTEGER,height INTEGER,latitude REAL,longitude REAL,altitude_m REAL,rtk_status TEXT,rtk_std_lat_m REAL,rtk_std_lon_m REAL,rtk_std_height_m REAL,rtk_correction_age_s REAL,rtk_altitude_type TEXT,thermal_source TEXT NOT NULL,quality_grade TEXT,raw_min INTEGER,raw_max INTEGER,raw_mean REAL,raw_median REAL,raw_p95 REAL,raw_p99 REAL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,frame_id));
CREATE TABLE IF NOT EXISTS image_pairs(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,pair_id TEXT NOT NULL,rgb_frame_id TEXT NOT NULL,thermal_frame_id TEXT NOT NULL,confidence REAL NOT NULL,method TEXT NOT NULL,distance_m REAL,time_delta_s REAL,PRIMARY KEY(project_id,pair_id),FOREIGN KEY(project_id,rgb_frame_id) REFERENCES image_frames(project_id,frame_id) ON DELETE CASCADE,FOREIGN KEY(project_id,thermal_frame_id) REFERENCES thermal_frames(project_id,frame_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS pv_modules(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,module_id TEXT NOT NULL,frame_id TEXT NOT NULL,polygon_json TEXT NOT NULL,detection_confidence REAL,detector TEXT NOT NULL,latitude REAL,longitude REAL,altitude_m REAL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,module_id));
CREATE TABLE IF NOT EXISTS findings(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,finding_id TEXT NOT NULL,thermal_frame_id TEXT NOT NULL,pixel_x INTEGER NOT NULL,pixel_y INTEGER NOT NULL,finding_type TEXT NOT NULL,confidence REAL,raw_value INTEGER,raw_delta_from_median REAL,temperature_c REAL,module_id TEXT,latitude REAL,longitude REAL,altitude_m REAL,reviewer_status TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,finding_id),FOREIGN KEY(project_id,thermal_frame_id) REFERENCES thermal_frames(project_id,frame_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS finding_reviews(review_id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL,finding_id TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('confirmed','rejected','unclear')),reviewer TEXT NOT NULL,reviewed_at_utc TEXT NOT NULL,note TEXT,FOREIGN KEY(project_id,finding_id) REFERENCES findings(project_id,finding_id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_findings_frame ON findings(project_id,thermal_frame_id); CREATE INDEX IF NOT EXISTS idx_reviews_finding ON finding_reviews(project_id,finding_id);
"""

def _upsert(table:str, columns:tuple[str,...], conflict:tuple[str,...])->str:
    names=','.join(columns); marks=','.join('?' for _ in columns); updates=','.join(f'{c}=excluded.{c}' for c in columns if c not in conflict)
    return f"INSERT INTO {table}({names}) VALUES ({marks}) ON CONFLICT({','.join(conflict)}) DO UPDATE SET {updates}"

class ProjectDatabase:
    def __init__(self,path:str|Path)->None:self.path=Path(path)
    @contextmanager
    def connect(self)->Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True,exist_ok=True);db=sqlite3.connect(self.path);db.row_factory=sqlite3.Row
        try:db.execute('PRAGMA foreign_keys=ON');yield db;db.commit()
        except Exception:db.rollback();raise
        finally:db.close()
    def initialize(self)->None:
        with self.connect() as db:
            db.executescript(_SCHEMA);row=db.execute('SELECT version FROM schema_info LIMIT 1').fetchone()
            if row is None:db.execute('INSERT INTO schema_info(version) VALUES (?)',(SCHEMA_VERSION,))
            elif row['version']!=SCHEMA_VERSION:raise RuntimeError(f"Unsupported database schema version: {row['version']}; migration required")
    def create_project(self,project_id:str,name:str)->None:
        with self.connect() as db:db.execute("INSERT INTO projects(project_id,name) VALUES (?,?) ON CONFLICT(project_id) DO UPDATE SET name=excluded.name",(project_id,name))
    def _save_thermal_frame(self,db,project_id,frame,quality):
        s=quality.statistics;p=frame.position;cols=('project_id','frame_id','source_file','timestamp_utc','camera_make','camera_model','width','height','latitude','longitude','altitude_m','rtk_status','rtk_std_lat_m','rtk_std_lon_m','rtk_std_height_m','rtk_correction_age_s','rtk_altitude_type','thermal_source','quality_grade','raw_min','raw_max','raw_mean','raw_median','raw_p95','raw_p99','metadata_json')
        db.execute(_upsert('thermal_frames',cols,('project_id','frame_id')),(project_id,frame.frame_id,str(frame.source_file),frame.timestamp_utc.isoformat() if frame.timestamp_utc else None,frame.camera_make,frame.camera_model,frame.thermal_width,frame.thermal_height,p.latitude if p else None,p.longitude if p else None,p.altitude_m if p else None,frame.rtk.status,frame.rtk.std_lat_m,frame.rtk.std_lon_m,frame.rtk.std_height_m,frame.rtk.correction_age_s,frame.rtk.altitude_type,frame.thermal_source,quality.grade.value,s.minimum,s.maximum,s.mean,s.median,s.p95,s.p99,json.dumps(frame.metadata,ensure_ascii=False)))
    def _save_findings(self,db,project_id,findings):
        cols=('project_id','finding_id','thermal_frame_id','pixel_x','pixel_y','finding_type','confidence','raw_value','raw_delta_from_median','temperature_c','module_id','latitude','longitude','altitude_m','reviewer_status','metadata_json');sql=_upsert('findings',cols,('project_id','finding_id'))
        db.executemany(sql,[(project_id,f.finding_id,f.thermal_frame_id,f.pixel_x,f.pixel_y,f.finding_type,f.confidence,f.raw_value,f.raw_delta_from_median,f.temperature_c,f.module_id,f.position.latitude if f.position else None,f.position.longitude if f.position else None,f.position.altitude_m if f.position else None,f.reviewer_status,json.dumps(f.metadata,ensure_ascii=False)) for f in findings])
    def save_thermal_frame(self,project_id,frame,quality):
        with self.connect() as db:self._save_thermal_frame(db,project_id,frame,quality)
    def save_findings(self,project_id,findings):
        with self.connect() as db:self._save_findings(db,project_id,findings)
    def save_thermal_result(self,project_id,frame,quality,findings):
        """Persist one frame and all of its findings in one transaction."""
        with self.connect() as db:self._save_thermal_frame(db,project_id,frame,quality);self._save_findings(db,project_id,findings)
    def save_image_frames(self,project_id,frames):
        cols=('project_id','frame_id','source_file','timestamp_utc','camera_make','camera_model','width','height','latitude','longitude','altitude_m','metadata_json');sql=_upsert('image_frames',cols,('project_id','frame_id'))
        with self.connect() as db:db.executemany(sql,[(project_id,f.frame_id,str(f.source_file),f.timestamp_utc.isoformat() if f.timestamp_utc else None,f.camera_make,f.camera_model,f.width,f.height,f.position.latitude if f.position else None,f.position.longitude if f.position else None,f.position.altitude_m if f.position else None,json.dumps(f.metadata,ensure_ascii=False)) for f in frames])
    def save_pairs(self,project_id,pairs):
        cols=('project_id','pair_id','rgb_frame_id','thermal_frame_id','confidence','method','distance_m','time_delta_s');sql=_upsert('image_pairs',cols,('project_id','pair_id'))
        with self.connect() as db:db.executemany(sql,[(project_id,p.pair_id,p.rgb_frame_id,p.thermal_frame_id,p.confidence,p.method,p.distance_m,p.time_delta_s) for p in pairs])
    def save_modules(self,project_id,modules):
        cols=('project_id','module_id','frame_id','polygon_json','detection_confidence','detector','latitude','longitude','altitude_m','metadata_json');sql=_upsert('pv_modules',cols,('project_id','module_id'))
        with self.connect() as db:db.executemany(sql,[(project_id,m.module_id,m.frame_id,json.dumps(m.polygon_px),m.detection_confidence,m.detector,m.position.latitude if m.position else None,m.position.longitude if m.position else None,m.position.altitude_m if m.position else None,json.dumps(m.metadata,ensure_ascii=False)) for m in modules])
    def save_review(self,review,*,project_id:str):
        with self.connect() as db:
            cur=db.execute('UPDATE findings SET reviewer_status=? WHERE project_id=? AND finding_id=?',(review.status.value,project_id,review.finding_id))
            if cur.rowcount!=1:raise KeyError(f'Unknown finding: {project_id}/{review.finding_id}')
            db.execute('INSERT INTO finding_reviews(project_id,finding_id,status,reviewer,reviewed_at_utc,note) VALUES (?,?,?,?,?,?)',(project_id,review.finding_id,review.status.value,review.reviewer,review.reviewed_at_utc.isoformat(),review.note))
