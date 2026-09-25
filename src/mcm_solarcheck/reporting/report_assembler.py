"""Assemble customer report contracts from persisted project and reviewed evidence."""
from __future__ import annotations
from datetime import datetime
from mcm_solarcheck.reporting.data import InspectionReportDataService
from mcm_solarcheck.reporting.model import build_report_model
from mcm_solarcheck.reporting.report_model import InspectionReport, ModuleReportDetail, OperatorSnapshot, ReportImage, ThermalMeasurement
from mcm_solarcheck.thermal.temperature_provenance import has_validated_celsius
from mcm_solarcheck.reporting.report_assets import build_detail_assets


def _address(*parts: str | None) -> str | None:
    values=[part.strip() for part in parts if isinstance(part,str) and part.strip()]
    return ", ".join(values) if values else None


def assemble_inspection_report(database, project_id: str, report_id: str, inspection_started_at: datetime, *, release_status: str="draft", asset_dir=None, operator_profile=None) -> InspectionReport:
    """Use project master data once; only human-confirmed evidence becomes a defect detail."""
    profile=database.project_profile(project_id)
    if profile is None:
        raise ValueError("project profile is required before report assembly")
    service=InspectionReportDataService(database)
    data=service.build(project_id)
    evidence_model=build_report_model(data)
    provenance_by_finding={item.finding.finding_id:item.finding for item in data.confirmed_findings}
    with database.connect() as sql:
        thermal_paths={row['frame_id']:row['source_file'] for row in sql.execute('SELECT frame_id,source_file FROM thermal_frames WHERE project_id=?',(project_id,))}
        rgb_paths={row['frame_id']:row['source_file'] for row in sql.execute('SELECT frame_id,source_file FROM image_frames WHERE project_id=?',(project_id,))}
    def detail(item):
        source=provenance_by_finding[item.finding_id]
        measurement=None
        if has_validated_celsius(source.temperature_c,source.temperature_status,source.temperature_provider):
            measurement=ThermalMeasurement(source.temperature_c,None,source.temperature_provider,True)
        thermal_path=thermal_paths.get(item.thermal_frame_id)
        rgb_path=rgb_paths.get(item.rgb_frame_id) if item.rgb_frame_id else None
        rgb_geometry=thermal_geometry="full_frame"
        if asset_dir is not None:
            assets=build_detail_assets(database,project_id,item.finding_id,item.module_id,asset_dir)
            by_modality={asset.modality:asset for asset in assets}
            if "rgb" in by_modality:
                rgb_path=str(by_modality["rgb"].path); rgb_geometry=by_modality["rgb"].geometry_source
            if "thermal" in by_modality:
                thermal_path=str(by_modality["thermal"].path); thermal_geometry=by_modality["thermal"].geometry_source
        return ModuleReportDetail(
            module_id=item.module_id,
            finding_label=item.classification,
            review_status="confirmed",
            rgb_image=ReportImage(item.rgb_frame_id,rgb_path,"rgb",rgb_geometry) if item.rgb_frame_id and rgb_path else None,
            thermal_image=ReportImage(item.thermal_frame_id,thermal_path,"thermal",thermal_geometry) if thermal_path else None,
            manual_inspection_required=False,
            thermal_measurement=measurement,
        )
    details=list(detail(item) for item in evidence_model.evidence if item.module_id is not None and item.module_id.strip())
    unclear=service.queries.findings(project_id,reviewer_status="unclear")
    unclear_module_ids={item.module_id.strip() for item in unclear if item.module_id is not None and item.module_id.strip()}
    for module_id in sorted(unclear_module_ids):
        details.append(ModuleReportDetail(module_id=module_id,finding_label=None,review_status="unclear",manual_inspection_required=True))
    details=tuple(details)
    resolved_module_ids={item.module_id.strip() for item in evidence_model.evidence if item.module_id is not None and item.module_id.strip()}
    unresolved=sum(1 for item in evidence_model.evidence if item.module_id is None or not item.module_id.strip())
    unresolved_unclear=sum(1 for item in unclear if item.module_id is None or not item.module_id.strip())
    if release_status=="released" and (data.summary.unreviewed_findings or unresolved or unresolved_unclear):
        raise ValueError("released report requires reviewed findings and resolved physical modules")
    return InspectionReport(
        report_id=report_id,
        project_id=project_id,
        customer_name=profile.customer_name,
        site_name=profile.site_name,
        inspection_started_at=inspection_started_at,
        inspector=profile.inspector,
        total_modules=data.summary.pv_modules,
        conspicuous_modules=len(resolved_module_ids),
        manual_review_modules=len(unclear_module_ids),
        site_address=_address(profile.site_street,profile.site_postal_code,profile.site_city),
        customer_contact=profile.customer_contact,
        customer_address=_address(profile.customer_street,profile.customer_postal_code,profile.customer_city),
        customer_email=profile.customer_email,
        customer_phone=profile.customer_phone,
        customer_reference=profile.customer_reference,
        order_reference=profile.order_reference,
        details=details,
        operator=(OperatorSnapshot(operator_profile.company_name,operator_profile.address,operator_profile.email,operator_profile.phone,operator_profile.website,operator_profile.tax_id,operator_profile.vat_id,operator_profile.logo_path) if operator_profile is not None else None),
        release_status=release_status,
    )
