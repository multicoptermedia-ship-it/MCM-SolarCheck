"""Vendor-neutral report model independent from DOCX/PDF rendering."""
from __future__ import annotations
from dataclasses import dataclass
from .data import InspectionReportData

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
    evidence=tuple(ReportEvidence(
        finding_id=item.finding.finding_id,
        classification=item.finding.finding_type,
        module_id=item.finding.module_id,
        thermal_frame_id=item.finding.thermal_frame_id,
        rgb_frame_id=item.rgb_frame_id,
        raw_value=item.finding.raw_value,
        raw_delta_from_median=item.finding.raw_delta_from_median,
        temperature_c=item.finding.temperature_c,
        latitude=item.finding.latitude,
        longitude=item.finding.longitude,
        reviewer=item.reviewer,
        review_note=item.review_note,
    ) for item in data.confirmed_findings)
    warnings=[]
    if not data.temperature_evidence_validated:
        warnings.append('Radiometric Celsius conversion has not been validated for all confirmed findings; raw sensor values must not be presented as degrees Celsius.')
    if data.summary.unreviewed_findings:
        warnings.append(f'{data.summary.unreviewed_findings} finding(s) remain unreviewed and are excluded from confirmed evidence.')
    status='review_complete' if data.summary.unreviewed_findings==0 else 'review_incomplete'
    temperature_statement=('Validated Celsius evidence is available for every confirmed finding.' if data.temperature_evidence_validated else 'Celsius evidence is incomplete or unvalidated; no temperature claim may be inferred from raw values.')
    return InspectionReportModel(data.project_id,'PV Thermal Inspection Report',data.project_name,status,temperature_statement,evidence,tuple(warnings))
