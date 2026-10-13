"""Conservative adapter from reviewed importer candidates to existing report model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mcm_solarcheck.reporting.report_model import (
    InspectionReport, ModuleReportDetail, ReportProvenance,
)
from mcm_solarcheck.services.vertical_m3t_candidate_analysis import ImportedCandidateAnalysis
from mcm_solarcheck.services.vertical_review_snapshot import ApprovedCandidateSnapshot, verify_review_snapshot


@dataclass(frozen=True)
class ReportContext:
    report_id: str
    project_id: str
    customer_name: str
    site_name: str
    inspection_started_at: datetime
    inspector: str
    total_modules: int
    software_version: str


def build_reviewed_inspection_report(
    analysis: ImportedCandidateAnalysis,
    snapshot: ApprovedCandidateSnapshot,
    context: ReportContext,
) -> InspectionReport:
    verify_review_snapshot(analysis, snapshot)
    if not isinstance(context, ReportContext):
        raise TypeError("explicit report context required")
    if context.inspector != snapshot.decision.reviewer_id:
        raise PermissionError("report inspector must match approving reviewer")
    if type(context.total_modules) is not int or context.total_modules <= 0:
        raise ValueError("measured total module count required")
    if not context.software_version.strip():
        raise ValueError("software version required")
    accepted = [f for f in analysis.candidates if f.finding_id in snapshot.accepted_ids]
    if any(not f.module_id or not f.finding_type.strip() for f in accepted):
        raise ValueError("accepted findings require expert-verified module assignment and label")
    module_ids = [f.module_id for f in accepted]
    if len(set(module_ids)) != len(module_ids):
        raise ValueError("multiple candidates per module require explicit aggregation")
    if len(module_ids) > context.total_modules:
        raise ValueError("accepted modules exceed measured module count")
    details = tuple(
        ModuleReportDetail(
            module_id=f.module_id,
            finding_label=f.finding_type,
            review_status="confirmed",
        ) for f in accepted
    )
    return InspectionReport(
        report_id=context.report_id,
        project_id=context.project_id,
        customer_name=context.customer_name,
        site_name=context.site_name,
        inspection_started_at=context.inspection_started_at,
        inspector=context.inspector,
        total_modules=context.total_modules,
        conspicuous_modules=len(details),
        manual_review_modules=0,
        details=details,
        provenance=ReportProvenance(
            software_version=context.software_version,
            evidence_statement=(
                "DJI M3T Rohwert-Auffaelligkeitskandidaten; fachlich einzeln "
                "geprueft; keine validierten Celsiuswerte. Review: "
                + snapshot.decision.evidence_reference
            ),
        ),
        release_status="reviewed",
    )
