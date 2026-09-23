"""Vendor-neutral report model independent from DOCX/PDF rendering."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from .data import InspectionReportData
from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.prioritization import prioritize_finding

@dataclass(frozen=True)
class ReportEvidence:
    finding_id:str
    classification:str
    module_id:str|None
    thermal_frame_id:str
    rgb_frame_id:str|None
    raw_value:int|None
    raw_delta_from_median:float|None
    temperature_c:float|None
    latitude:float|None
    longitude:float|None
    reviewer:str|None
    review_note:str|None
    priority_level:str='unrated'
    priority_score:float|None=None

@dataclass(frozen=True)
class InspectionReportModel:
    project_id:str
    title:str
    project_name:str
    inspection_status:str
    temperature_statement:str
    evidence:tuple[ReportEvidence,...]
    warnings:tuple[str,...]

def build_report_model(data:InspectionReportData)->InspectionReportModel:
    """Translate persisted evidence into a renderer-independent report contract."""
    def valid_gps(latitude,longitude):
        return latitude is not None and longitude is not None and isfinite(float(latitude)) and isfinite(float(longitude)) and -90<=latitude<=90 and -180<=longitude<=180
    def priority(item):
        record=item.finding
        finding=Finding(record.finding_id,record.thermal_frame_id,record.pixel_x,record.pixel_y,record.finding_type,record.confidence,record.raw_value,record.raw_delta_from_median,record.temperature_c,record.module_id)
        return prioritize_finding(finding)
    evidence=tuple(ReportEvidence(
        finding_id=item.finding.finding_id,
        classification=item.finding.finding_type,
        module_id=item.finding.module_id,
        thermal_frame_id=item.finding.thermal_frame_id,
        rgb_frame_id=item.rgb_frame_id,
        raw_value=item.finding.raw_value,
        raw_delta_from_median=item.finding.raw_delta_from_median,
        temperature_c=item.finding.temperature_c,
        latitude=item.finding.latitude if valid_gps(item.finding.latitude,item.finding.longitude) else None,
        longitude=item.finding.longitude if valid_gps(item.finding.latitude,item.finding.longitude) else None,
        reviewer=item.reviewer,
        review_note=item.review_note,
        priority_level=priority(item).level,
        priority_score=priority(item).score,
    ) for item in data.confirmed_findings)
    evidence=tuple(sorted(evidence,key=lambda item:(item.priority_level!='review',-(item.priority_score if item.priority_score is not None else -1.0),item.module_id is None,item.module_id or '',item.finding_id)))
    warnings=[]
    if not data.temperature_evidence_validated:
        warnings.append('Radiometric Celsius conversion has not been validated for all confirmed findings; raw sensor values must not be presented as degrees Celsius.')
    if data.summary.unreviewed_findings:
        warnings.append(f'{data.summary.unreviewed_findings} finding(s) remain unreviewed and are excluded from confirmed evidence.')
    status='review_complete' if data.summary.unreviewed_findings==0 else 'review_incomplete'
    temperature_statement=('Validated Celsius evidence is available for every confirmed finding.' if data.temperature_evidence_validated else 'Celsius evidence is incomplete or unvalidated; no temperature claim may be inferred from raw values.')
    return InspectionReportModel(data.project_id,'PV Thermal Inspection Report',data.project_name,status,temperature_statement,evidence,tuple(warnings))
