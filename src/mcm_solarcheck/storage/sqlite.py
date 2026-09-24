"""SQLite persistence for MCM-SolarCheck inspection projects."""
from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
import json, sqlite3
from typing import Iterator
from mcm_solarcheck.domain.models import Finding, ImageFrame, ImagePair, PVModule, ThermalFrame
from mcm_solarcheck.review.training_corpus import index_m3t_training_sample

SCHEMA_VERSION = 10
_SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_info(version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS image_frames(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,frame_id TEXT NOT NULL,source_file TEXT NOT NULL,timestamp_utc TEXT,camera_make TEXT,camera_model TEXT,width INTEGER,height INTEGER,latitude REAL,longitude REAL,altitude_m REAL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,frame_id));
CREATE TABLE IF NOT EXISTS thermal_frames(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,frame_id TEXT NOT NULL,source_file TEXT NOT NULL,timestamp_utc TEXT,camera_make TEXT,camera_model TEXT,width INTEGER,height INTEGER,latitude REAL,longitude REAL,altitude_m REAL,rtk_status TEXT,rtk_std_lat_m REAL,rtk_std_lon_m REAL,rtk_std_height_m REAL,rtk_correction_age_s REAL,rtk_altitude_type TEXT,thermal_source TEXT NOT NULL,quality_grade TEXT,raw_min INTEGER,raw_max INTEGER,raw_mean REAL,raw_median REAL,raw_p95 REAL,raw_p99 REAL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,frame_id));
CREATE TABLE IF NOT EXISTS image_pairs(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,pair_id TEXT NOT NULL,rgb_frame_id TEXT NOT NULL,thermal_frame_id TEXT NOT NULL,confidence REAL NOT NULL,method TEXT NOT NULL,distance_m REAL,time_delta_s REAL,PRIMARY KEY(project_id,pair_id),FOREIGN KEY(project_id,rgb_frame_id) REFERENCES image_frames(project_id,frame_id) ON DELETE CASCADE,FOREIGN KEY(project_id,thermal_frame_id) REFERENCES thermal_frames(project_id,frame_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS pv_modules(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,module_id TEXT NOT NULL,frame_id TEXT NOT NULL,polygon_json TEXT NOT NULL,detection_confidence REAL,detector TEXT NOT NULL,latitude REAL,longitude REAL,altitude_m REAL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,module_id));
CREATE TABLE IF NOT EXISTS module_identity_links(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,frame_id TEXT NOT NULL,local_module_id TEXT NOT NULL,physical_module_id TEXT NOT NULL,status TEXT NOT NULL,normalized_distance REAL,PRIMARY KEY(project_id,frame_id,local_module_id));
CREATE INDEX IF NOT EXISTS idx_module_identity_physical ON module_identity_links(project_id,physical_module_id);
CREATE TABLE IF NOT EXISTS findings(project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,finding_id TEXT NOT NULL,thermal_frame_id TEXT NOT NULL,pixel_x INTEGER NOT NULL,pixel_y INTEGER NOT NULL,finding_type TEXT NOT NULL,confidence REAL,raw_value INTEGER,raw_delta_from_median REAL,temperature_c REAL,module_id TEXT,latitude REAL,longitude REAL,altitude_m REAL,reviewer_status TEXT NOT NULL,metadata_json TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(project_id,finding_id),FOREIGN KEY(project_id,thermal_frame_id) REFERENCES thermal_frames(project_id,frame_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS finding_sensor_links(project_id TEXT NOT NULL,finding_id TEXT NOT NULL,rgb_frame_id TEXT NOT NULL,pair_id TEXT,pair_confidence REAL,rgb_pixel_x REAL,rgb_pixel_y REAL,transform_method TEXT NOT NULL,transform_validated INTEGER NOT NULL CHECK(transform_validated IN (0,1)),transform_error_px REAL,status TEXT NOT NULL,candidates_json TEXT NOT NULL DEFAULT '[]',PRIMARY KEY(project_id,finding_id),FOREIGN KEY(project_id,finding_id) REFERENCES findings(project_id,finding_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS finding_reviews(review_id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL,finding_id TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('confirmed','rejected','unclear')),reviewer TEXT NOT NULL,reviewed_at_utc TEXT NOT NULL,note TEXT,FOREIGN KEY(project_id,finding_id) REFERENCES findings(project_id,finding_id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS training_samples(sample_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,source_frame_id TEXT NOT NULL,source_file TEXT NOT NULL,modality TEXT NOT NULL CHECK(modality IN ('thermal','rgb')),content_sha256 TEXT NOT NULL,label_status TEXT NOT NULL,rights_status TEXT NOT NULL,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS training_labels(label_id INTEGER PRIMARY KEY AUTOINCREMENT,project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,source_frame_id TEXT NOT NULL,module_id TEXT,finding_id TEXT,defect_class TEXT NOT NULL,reviewer TEXT NOT NULL,supersedes_label_id INTEGER REFERENCES training_labels(label_id),note TEXT,inspection_group_id TEXT,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_training_labels_frame ON training_labels(project_id,source_frame_id);
CREATE INDEX IF NOT EXISTS idx_training_samples_project ON training_samples(project_id,modality,label_status,rights_status);
CREATE INDEX IF NOT EXISTS idx_findings_frame ON findings(project_id,thermal_frame_id); CREATE INDEX IF NOT EXISTS idx_reviews_finding ON finding_reviews(project_id,finding_id); CREATE INDEX IF NOT EXISTS idx_sensor_links_rgb ON finding_sensor_links(project_id,rgb_frame_id);
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
            tables={row['name'] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
            if tables:
                if 'schema_info' not in tables:raise RuntimeError('Unversioned non-empty database; refusing to modify it')
                row=db.execute('SELECT version FROM schema_info LIMIT 1').fetchone()
                if row is None or row['version']!=SCHEMA_VERSION:
                    version=None if row is None else row['version'];raise RuntimeError(f"Unsupported database schema version: {version}; migration required")
                return
            db.executescript(_SCHEMA);db.execute('INSERT INTO schema_info(version) VALUES (?)',(SCHEMA_VERSION,))
    def create_project(self,project_id:str,name:str)->None:
        with self.connect() as db:db.execute("INSERT INTO projects(project_id,name) VALUES (?,?) ON CONFLICT(project_id) DO UPDATE SET name=excluded.name",(project_id,name))
    def _save_thermal_frame(self,db,project_id,frame,quality):
        s=quality.statistics;p=frame.position;cols=('project_id','frame_id','source_file','timestamp_utc','camera_make','camera_model','width','height','latitude','longitude','altitude_m','rtk_status','rtk_std_lat_m','rtk_std_lon_m','rtk_std_height_m','rtk_correction_age_s','rtk_altitude_type','thermal_source','quality_grade','raw_min','raw_max','raw_mean','raw_median','raw_p95','raw_p99','metadata_json')
        db.execute(_upsert('thermal_frames',cols,('project_id','frame_id')),(project_id,frame.frame_id,str(frame.source_file),frame.timestamp_utc.isoformat() if frame.timestamp_utc else None,frame.camera_make,frame.camera_model,frame.thermal_width,frame.thermal_height,p.latitude if p else None,p.longitude if p else None,p.altitude_m if p else None,frame.rtk.status,frame.rtk.std_lat_m,frame.rtk.std_lon_m,frame.rtk.std_height_m,frame.rtk.correction_age_s,frame.rtk.altitude_type,frame.thermal_source,quality.grade.value,s.minimum,s.maximum,s.mean,s.median,s.p95,s.p99,json.dumps(frame.metadata,ensure_ascii=False)))
    def _save_findings(self,db,project_id,findings):
        cols=('project_id','finding_id','thermal_frame_id','pixel_x','pixel_y','finding_type','confidence','raw_value','raw_delta_from_median','temperature_c','module_id','latitude','longitude','altitude_m','reviewer_status','metadata_json');sql=_upsert('findings',cols,('project_id','finding_id'))
        db.executemany(sql,[(project_id,f.finding_id,f.thermal_frame_id,f.pixel_x,f.pixel_y,f.finding_type,f.confidence,f.raw_value,f.raw_delta_from_median,f.temperature_c,f.module_id,f.position.latitude if f.position else None,f.position.longitude if f.position else None,f.position.altitude_m if f.position else None,f.reviewer_status,json.dumps(f.metadata,ensure_ascii=False)) for f in findings])
    def _sensor_link_values(self,project_id:str,finding:Finding):
        m=finding.metadata
        if 'cross_sensor_status' not in m or 'rgb_frame_id' not in m:return None
        def number(key):
            value=m.get(key);return None if value is None else float(value)
        candidates=tuple(v for v in m.get('cross_sensor_candidates','').split(',') if v)
        return (project_id,finding.finding_id,m['rgb_frame_id'],m.get('pair_id'),number('pair_confidence'),number('rgb_pixel_x'),number('rgb_pixel_y'),m.get('transform_method','unknown'),1 if m.get('transform_validated')=='true' else 0,number('transform_error_px'),m['cross_sensor_status'],json.dumps(candidates))
    def _save_sensor_links(self,db,project_id,findings):
        cols=('project_id','finding_id','rgb_frame_id','pair_id','pair_confidence','rgb_pixel_x','rgb_pixel_y','transform_method','transform_validated','transform_error_px','status','candidates_json');sql=_upsert('finding_sensor_links',cols,('project_id','finding_id'))
        rows=[v for f in findings if (v:=self._sensor_link_values(project_id,f)) is not None]
        if rows:db.executemany(sql,rows)
    def _training_sample_values(self,project_id,frame,modality):
        sample=index_m3t_training_sample(frame.frame_id, frame.source_file, modality)
        return (sample.sample_id,project_id,sample.source_frame_id,sample.source_file,sample.modality,sample.content_sha256,sample.label_status,sample.rights_status)
    def _save_training_frame(self,db,project_id,frame,modality):
        # Persistence tests and legacy projects may reference source paths that
        # are not locally available. Project persistence must still succeed;
        # corpus intake occurs only when the actual image bytes are present.
        if not Path(frame.source_file).is_file():return
        cols=('sample_id','project_id','source_frame_id','source_file','modality','content_sha256','label_status','rights_status')
        db.execute(_upsert('training_samples',cols,('sample_id',)),self._training_sample_values(project_id,frame,modality))
    def save_thermal_frame(self,project_id,frame,quality):
        with self.connect() as db:
            self._save_thermal_frame(db,project_id,frame,quality)
            self._save_training_frame(db,project_id,frame,'thermal')
    def save_findings(self,project_id,findings):
        findings=tuple(findings)
        with self.connect() as db:self._save_findings(db,project_id,findings);self._save_sensor_links(db,project_id,findings)
    def save_thermal_result(self,project_id,frame,quality,findings):
        findings=tuple(findings)
        with self.connect() as db:self._save_thermal_frame(db,project_id,frame,quality);self._save_training_frame(db,project_id,frame,'thermal');self._save_findings(db,project_id,findings);self._save_sensor_links(db,project_id,findings)
    def save_image_frames(self,project_id,frames):
        cols=('project_id','frame_id','source_file','timestamp_utc','camera_make','camera_model','width','height','latitude','longitude','altitude_m','metadata_json');sql=_upsert('image_frames',cols,('project_id','frame_id'))
        frames=tuple(frames)
        with self.connect() as db:
            db.executemany(sql,[(project_id,f.frame_id,str(f.source_file),f.timestamp_utc.isoformat() if f.timestamp_utc else None,f.camera_make,f.camera_model,f.width,f.height,f.position.latitude if f.position else None,f.position.longitude if f.position else None,f.position.altitude_m if f.position else None,json.dumps(f.metadata,ensure_ascii=False)) for f in frames])
            for frame in frames:self._save_training_frame(db,project_id,frame,'rgb')
    def save_pairs(self,project_id,pairs):
        cols=('project_id','pair_id','rgb_frame_id','thermal_frame_id','confidence','method','distance_m','time_delta_s');sql=_upsert('image_pairs',cols,('project_id','pair_id'))
        with self.connect() as db:db.executemany(sql,[(project_id,p.pair_id,p.rgb_frame_id,p.thermal_frame_id,p.confidence,p.method,p.distance_m,p.time_delta_s) for p in pairs])
    def save_modules(self,project_id,modules):
        cols=('project_id','module_id','frame_id','polygon_json','detection_confidence','detector','latitude','longitude','altitude_m','metadata_json');sql=_upsert('pv_modules',cols,('project_id','module_id'))
        with self.connect() as db:db.executemany(sql,[(project_id,m.module_id,m.frame_id,json.dumps(m.polygon_px),m.detection_confidence,m.detector,m.position.latitude if m.position else None,m.position.longitude if m.position else None,m.position.altitude_m if m.position else None,json.dumps(m.metadata,ensure_ascii=False)) for m in modules])
    def save_module_identity_assignments(self,project_id,assignments):
        cols=('project_id','frame_id','local_module_id','physical_module_id','status','normalized_distance');sql=_upsert('module_identity_links',cols,('project_id','frame_id','local_module_id'))
        rows=[(project_id,a.observation.frame_id,a.observation.local_id,a.module_id,a.status,a.normalized_distance) for a in assignments if a.module_id is not None]
        with self.connect() as db:
            if rows:db.executemany(sql,rows)
    def save_modules_with_identities(self,project_id,modules,assignments):
        modules=tuple(modules);assignments=tuple(assignments)
        module_keys={(m.frame_id,m.module_id) for m in modules};assignment_keys={(a.observation.frame_id,a.observation.local_id) for a in assignments}
        if not assignment_keys.issubset(module_keys):raise ValueError('identity assignment does not reference persisted module')
        mcols=('project_id','module_id','frame_id','polygon_json','detection_confidence','detector','latitude','longitude','altitude_m','metadata_json');msql=_upsert('pv_modules',mcols,('project_id','module_id'))
        icols=('project_id','frame_id','local_module_id','physical_module_id','status','normalized_distance');isql=_upsert('module_identity_links',icols,('project_id','frame_id','local_module_id'))
        mrows=[(project_id,m.module_id,m.frame_id,json.dumps(m.polygon_px),m.detection_confidence,m.detector,m.position.latitude if m.position else None,m.position.longitude if m.position else None,m.position.altitude_m if m.position else None,json.dumps(m.metadata,ensure_ascii=False)) for m in modules]
        irows=[(project_id,a.observation.frame_id,a.observation.local_id,a.module_id,a.status,a.normalized_distance) for a in assignments if a.module_id is not None]
        with self.connect() as db:
            if mrows:db.executemany(msql,mrows)
            if irows:db.executemany(isql,irows)
    def save_modules_identities_and_findings(self,project_id,modules,assignments,findings):
        modules=tuple(modules);assignments=tuple(assignments);findings=tuple(findings)
        module_keys={(m.frame_id,m.module_id) for m in modules};assignment_keys={(a.observation.frame_id,a.observation.local_id) for a in assignments}
        if not assignment_keys.issubset(module_keys):raise ValueError('identity assignment does not reference persisted module')
        assigned_ids={m.module_id for m in modules}
        for finding in findings:
            if finding.module_id is not None and finding.module_id not in assigned_ids:raise ValueError('finding references module outside atomic persistence batch')
        mcols=('project_id','module_id','frame_id','polygon_json','detection_confidence','detector','latitude','longitude','altitude_m','metadata_json');msql=_upsert('pv_modules',mcols,('project_id','module_id'))
        icols=('project_id','frame_id','local_module_id','physical_module_id','status','normalized_distance');isql=_upsert('module_identity_links',icols,('project_id','frame_id','local_module_id'))
        mrows=[(project_id,m.module_id,m.frame_id,json.dumps(m.polygon_px),m.detection_confidence,m.detector,m.position.latitude if m.position else None,m.position.longitude if m.position else None,m.position.altitude_m if m.position else None,json.dumps(m.metadata,ensure_ascii=False)) for m in modules]
        irows=[(project_id,a.observation.frame_id,a.observation.local_id,a.module_id,a.status,a.normalized_distance) for a in assignments if a.module_id is not None]
        with self.connect() as db:
            if mrows:db.executemany(msql,mrows)
            if irows:db.executemany(isql,irows)
            self._save_findings(db,project_id,findings);self._save_sensor_links(db,project_id,findings)
    def save_finding_sensor_link(self,project_id:str,finding:Finding)->None:
        values=self._sensor_link_values(project_id,finding)
        if values is None:raise ValueError('finding has no cross-sensor linkage metadata')
        cols=('project_id','finding_id','rgb_frame_id','pair_id','pair_confidence','rgb_pixel_x','rgb_pixel_y','transform_method','transform_validated','transform_error_px','status','candidates_json')
        with self.connect() as db:db.execute(_upsert('finding_sensor_links',cols,('project_id','finding_id')),values)
    def save_review(self,review,*,project_id:str):
        with self.connect() as db:
            cur=db.execute('UPDATE findings SET reviewer_status=? WHERE project_id=? AND finding_id=?',(review.status.value,project_id,review.finding_id))
            if cur.rowcount!=1:raise KeyError(f'Unknown finding: {project_id}/{review.finding_id}')
            db.execute('INSERT INTO finding_reviews(project_id,finding_id,status,reviewer,reviewed_at_utc,note) VALUES (?,?,?,?,?,?)',(project_id,review.finding_id,review.status.value,review.reviewer,review.reviewed_at_utc.isoformat(),review.note))

    def save_training_samples(self,project_id,samples):
        cols=('sample_id','project_id','source_frame_id','source_file','modality','content_sha256','label_status','rights_status')
        sql=_upsert('training_samples',cols,('sample_id',))
        rows=[(s.sample_id,project_id,s.source_frame_id,s.source_file,s.modality,s.content_sha256,s.label_status,s.rights_status) for s in samples]
        with self.connect() as db:
            if rows:db.executemany(sql,rows)

    def approve_training_frame(self,project_id,source_frame_id,*,rights_approved=False):
        with self.connect() as db:
            values=['human_reviewed']
            sql="UPDATE training_samples SET label_status=?"
            if rights_approved:
                sql+=", rights_status='approved'"
            sql+=" WHERE project_id=? AND source_frame_id=?"
            values.extend((project_id,source_frame_id))
            cur=db.execute(sql,tuple(values))
            if cur.rowcount < 1:raise KeyError(f'Unknown training frame: {project_id}/{source_frame_id}')
    def training_samples(self,project_id,*,trainable_only=False):
        sql='SELECT sample_id,source_frame_id,source_file,modality,content_sha256,label_status,rights_status FROM training_samples WHERE project_id=?'
        params=[project_id]
        if trainable_only:
            sql+=" AND label_status='human_reviewed' AND rights_status='approved'"
        sql+=' ORDER BY source_frame_id,sample_id'
        with self.connect() as db:return tuple(dict(row) for row in db.execute(sql,tuple(params)).fetchall())

    def save_ground_truth(self,project_id,label):
        with self.connect() as db:
            sample=db.execute('SELECT 1 FROM training_samples WHERE project_id=? AND source_frame_id=?',(project_id,label.source_frame_id)).fetchone()
            if sample is None:raise KeyError(f'No training sample for frame: {project_id}/{label.source_frame_id}')
            if label.supersedes_label_id is not None:
                previous=db.execute('SELECT project_id,source_frame_id,module_id,finding_id FROM training_labels WHERE label_id=?',(label.supersedes_label_id,)).fetchone()
                if previous is None:raise KeyError(f'Unknown superseded training label: {label.supersedes_label_id}')
                if previous['project_id']!=project_id or previous['source_frame_id']!=label.source_frame_id:raise ValueError('ground-truth correction must stay on the same project/frame')
                if previous['module_id']!=label.module_id or previous['finding_id']!=label.finding_id:raise ValueError('ground-truth correction must preserve its physical reference')
            db.execute('INSERT INTO training_labels(project_id,source_frame_id,module_id,finding_id,defect_class,reviewer,supersedes_label_id,note,inspection_group_id) VALUES (?,?,?,?,?,?,?,?,?)',(project_id,label.source_frame_id,label.module_id,label.finding_id,label.defect_class.value,label.reviewer,label.supersedes_label_id,label.note,label.inspection_group_id))
            db.execute("UPDATE training_samples SET label_status='human_reviewed' WHERE project_id=? AND source_frame_id=?",(project_id,label.source_frame_id))

    def ground_truth(self,project_id,source_frame_id=None):
        sql='SELECT label_id,source_frame_id,module_id,finding_id,defect_class,reviewer,supersedes_label_id,note,inspection_group_id FROM training_labels WHERE project_id=?'
        params=[project_id]
        if source_frame_id is not None:sql+=' AND source_frame_id=?';params.append(source_frame_id)
        sql+=' ORDER BY label_id'
        with self.connect() as db:return tuple(dict(row) for row in db.execute(sql,tuple(params)).fetchall())
