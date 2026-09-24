"""Assemble customer report contracts from persisted project and reviewed evidence."""
from __future__ import annotations
from datetime import datetime
from mcm_solarcheck.reporting.data import InspectionReportDataService
from mcm_solarcheck.reporting.model import build_report_model
from mcm_solarcheck.reporting.report_model import InspectionReport, ModuleReportDetail, ThermalMeasurement
from mcm_solarcheck.thermal.temperature_provenance import has_validated_celsius


def _address(*parts: str | None) -> str | None:
    values=[part.strip() for part in parts if isinstance(part,str) and part.strip()]
    return ", ".join(values) if values else None


def assemble_inspection_report(database, project_id: str, report_id: str, inspection_started_at: datetime, *, release_status: str="draft") -> InspectionReport:
    """Use project master data once; only human-confirmed evidence becomes a defect detail."""
    profile=database.project_profile(project_id)
    if profile is None:
        raise ValueError("project profile is required before report assembly")
    data=InspectionReportDataService(database).build(project_id)
    evidence_model=build_report_model(data)
    provenance_by_finding={item.finding.finding_id:item.finding for item in data.confirmed_findings}
    def detail(item):
        source=provenance_by_finding[item.finding_id]
        measurement=None
        if has_validated_celsius(source.temperature_c,source.temperature_status,source.temperature_provider):
            measurement=ThermalMeasurement(source.temperature_c,None,source.temperature_provider,True)
        return ModuleReportDetail(
            module_id=item.module_id,
            finding_label=item.classification,
            review_status="confirmed",
            manual_inspection_required=False,
            thermal_measurement=measurement,
        )
    details=tuple(detail(item) for item in evidence_model.evidence if item.module_id is not None and item.module_id.strip())
    unresolved=sum(1 for item in evidence_model.evidence if item.module_id is None or not item.module_id.strip())
    if release_status=="released" and (data.summary.unreviewed_findings or unresolved):
        raise ValueError("released report requires reviewed findings and resolved physical modules")
    return InspectionReport(
        report_id=report_id,
        project_id=project_id,
        customer_name=profile.customer_name,
        site_name=profile.site_name,
        inspection_started_at=inspection_started_at,
        inspector=profile.inspector,
        total_modules=data.summary.pv_modules,
        conspicuous_modules=data.summary.confirmed_findings,
        manual_review_modules=data.summary.unclear_findings + unresolved,
        site_address=_address(profile.site_street,profile.site_postal_code,profile.site_city),
        customer_contact=profile.customer_contact,
        customer_address=_address(profile.customer_street,profile.customer_postal_code,profile.customer_city),
        customer_email=profile.customer_email,
        customer_phone=profile.customer_phone,
        customer_reference=profile.customer_reference,
        order_reference=profile.order_reference,
        details=details,
        release_status=release_status,
    )
