"""Read-only inspection queries for review screens and reporting.

The query layer deliberately distinguishes calibrated Celsius evidence from raw
sensor values. Missing calibration is represented as ``None`` and is never
silently converted or estimated.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
from .sqlite import ProjectDatabase
from mcm_solarcheck.thermal.temperature_provenance import has_validated_celsius

@dataclass(frozen=True)
class InspectionSummary:
    project_id: str
    rgb_frames: int
    thermal_frames: int
    image_pairs: int
    pv_modules: int
    findings: int
    unreviewed_findings: int
    confirmed_findings: int
    rejected_findings: int
    unclear_findings: int
    calibrated_findings: int

@dataclass(frozen=True)
class FindingRecord:
    finding_id: str
    thermal_frame_id: str
    module_id: str | None
    pixel_x: int
    pixel_y: int
    finding_type: str
    confidence: float | None
    raw_value: int | None
    raw_delta_from_median: float | None
    temperature_c: float | None
    reviewer_status: str
    latitude: float | None
    longitude: float | None
    altitude_m: float | None
    rgb_frame_id: str | None = None
    pair_id: str | None = None
    pair_confidence: float | None = None
    rgb_pixel_x: float | None = None
    rgb_pixel_y: float | None = None
    transform_method: str | None = None
    transform_validated: bool | None = None
    transform_error_px: float | None = None
    cross_sensor_status: str | None = None
    temperature_status: str | None = None
    temperature_provider: str | None = None

@dataclass(frozen=True)
class ModuleIdentityRecord:
    frame_id:str
    local_module_id:str
    physical_module_id:str
    status:str
    normalized_distance:float|None

class InspectionQueries:
    """Stable read boundary between SQLite and UI/report generation."""
    def __init__(self,database:ProjectDatabase)->None:self.database=database
    def summary(self,project_id:str)->InspectionSummary:
        with self.database.connect() as db:
            project=db.execute('SELECT 1 FROM projects WHERE project_id=?',(project_id,)).fetchone()
            if project is None:raise KeyError(f'Unknown project: {project_id}')
            def count(table:str)->int:return int(db.execute(f'SELECT COUNT(*) FROM {table} WHERE project_id=?',(project_id,)).fetchone()[0])
            statuses={row['reviewer_status']:int(row['n']) for row in db.execute('SELECT reviewer_status, COUNT(*) AS n FROM findings WHERE project_id=? GROUP BY reviewer_status',(project_id,))}
            calibrated=0
            for row in db.execute('SELECT temperature_c, metadata_json FROM findings WHERE project_id=?',(project_id,)):
                if row['temperature_c'] is None:
                    continue
                try:
                    metadata=json.loads(row['metadata_json'] or '{}')
                except (TypeError,json.JSONDecodeError):
                    continue
                if isinstance(metadata,dict) and has_validated_celsius(row['temperature_c'],metadata.get('temperature_status'),metadata.get('temperature_provider')):
                    calibrated+=1
            return InspectionSummary(project_id,count('image_frames'),count('thermal_frames'),count('image_pairs'),count('pv_modules'),count('findings'),statuses.get('unreviewed',0),statuses.get('confirmed',0),statuses.get('rejected',0),statuses.get('unclear',0),calibrated)
    def module_identities(self,project_id:str,*,physical_module_id:str|None=None)->tuple[ModuleIdentityRecord,...]:
        sql='SELECT frame_id,local_module_id,physical_module_id,status,normalized_distance FROM module_identity_links WHERE project_id=?'
        params=[project_id]
        if physical_module_id is not None:sql+=' AND physical_module_id=?';params.append(physical_module_id)
        sql+=' ORDER BY physical_module_id,frame_id,local_module_id'
        with self.database.connect() as db:rows=db.execute(sql,tuple(params)).fetchall()
        return tuple(ModuleIdentityRecord(**dict(row)) for row in rows)
    def findings(self,project_id:str,*,reviewer_status:str|None=None,confirmed_only:bool=False)->tuple[FindingRecord,...]:
        if confirmed_only and reviewer_status is not None:raise ValueError('Use either confirmed_only or reviewer_status, not both')
        status='confirmed' if confirmed_only else reviewer_status
        sql='''SELECT f.finding_id,f.thermal_frame_id,f.module_id,f.pixel_x,f.pixel_y,
                      f.finding_type,f.confidence,f.raw_value,f.raw_delta_from_median,
                      f.temperature_c,f.reviewer_status,f.latitude,f.longitude,f.altitude_m,
                      l.rgb_frame_id,l.pair_id,l.pair_confidence,l.rgb_pixel_x,l.rgb_pixel_y,
                      l.transform_method,l.transform_validated,l.transform_error_px,
                      l.status AS cross_sensor_status,f.metadata_json
               FROM findings f LEFT JOIN finding_sensor_links l
                 ON l.project_id=f.project_id AND l.finding_id=f.finding_id
               WHERE f.project_id=?'''
        params:list[object]=[project_id]
        if status is not None:sql+=' AND f.reviewer_status=?';params.append(status)
        sql+=' ORDER BY f.thermal_frame_id,f.pixel_y,f.pixel_x,f.finding_id'
        with self.database.connect() as db:rows=db.execute(sql,tuple(params)).fetchall()
        records=[]
        for row in rows:
            values=dict(row)
            try:
                metadata=json.loads(values.pop('metadata_json') or '{}')
            except (TypeError,json.JSONDecodeError):
                metadata={}
            if not isinstance(metadata,dict):
                metadata={}
            values['temperature_status']=metadata.get('temperature_status')
            values['temperature_provider']=metadata.get('temperature_provider')
            if values['transform_validated'] is not None:values['transform_validated']=bool(values['transform_validated'])
            records.append(FindingRecord(**values))
        return tuple(records)
