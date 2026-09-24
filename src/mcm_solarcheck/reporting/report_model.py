"""Backend-neutral inspection report contract."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite


def _text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value.strip()


@dataclass(frozen=True)
class IrradianceSummary:
    mean_w_m2: float
    source: str
    minimum_w_m2: float | None = None
    maximum_w_m2: float | None = None

    def __post_init__(self) -> None:
        _text("source", self.source)
        values=[self.mean_w_m2]
        if self.minimum_w_m2 is not None: values.append(self.minimum_w_m2)
        if self.maximum_w_m2 is not None: values.append(self.maximum_w_m2)
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(float(v)) or v < 0 for v in values):
            raise ValueError("irradiance values must be finite non-negative numbers")
        if self.minimum_w_m2 is not None and self.mean_w_m2 < self.minimum_w_m2:
            raise ValueError("mean irradiance must not be below minimum")
        if self.maximum_w_m2 is not None and self.mean_w_m2 > self.maximum_w_m2:
            raise ValueError("mean irradiance must not exceed maximum")


@dataclass(frozen=True)
class EquipmentRecord:
    name: str
    identifier: str | None = None
    calibration_reference: str | None = None

    def __post_init__(self) -> None:
        _text("equipment name", self.name)
        for n,v in (("identifier",self.identifier),("calibration_reference",self.calibration_reference)):
            if v is not None: _text(n,v)


@dataclass(frozen=True)
class ReportProvenance:
    software_version: str
    evidence_statement: str

    def __post_init__(self) -> None:
        _text("software_version",self.software_version); _text("evidence_statement",self.evidence_statement)


@dataclass(frozen=True)
class ThermalMeasurement:
    temperature_c: float
    delta_t_c: float | None
    provider: str
    provenance_validated: bool

    def __post_init__(self) -> None:
        _text("provider",self.provider)
        values=(self.temperature_c,) if self.delta_t_c is None else (self.temperature_c,self.delta_t_c)
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(float(v)) for v in values):
            raise ValueError("thermal measurements must be finite numbers")
        if self.provenance_validated is not True:
            raise ValueError("Celsius report values require validated radiometric provenance")


@dataclass(frozen=True)
class ReportImage:
    source_frame_id: str
    path: str
    modality: str

    def __post_init__(self) -> None:
        _text("source_frame_id",self.source_frame_id); _text("path",self.path)
        if self.modality not in {"rgb","thermal"}:
            raise ValueError("report image modality must be rgb or thermal")


@dataclass(frozen=True)
class ModuleReportDetail:
    module_id: str
    finding_label: str
    review_status: str
    rgb_image: ReportImage | None = None
    thermal_image: ReportImage | None = None
    manual_inspection_required: bool = False
    thermal_measurement: ThermalMeasurement | None = None

    def __post_init__(self) -> None:
        _text("module_id",self.module_id); _text("finding_label",self.finding_label)
        if self.review_status not in {"confirmed","unclear"}:
            raise ValueError("customer detail requires a reviewed confirmed/unclear status")
        if not isinstance(self.manual_inspection_required,bool):
            raise ValueError("manual_inspection_required must be boolean")
        if self.rgb_image and self.rgb_image.modality!="rgb": raise ValueError("rgb_image must be RGB")
        if self.thermal_image and self.thermal_image.modality!="thermal": raise ValueError("thermal_image must be thermal")


@dataclass(frozen=True)
class InspectionReport:
    report_id: str
    project_id: str
    customer_name: str
    site_name: str
    inspection_started_at: datetime
    inspector: str
    total_modules: int
    conspicuous_modules: int
    manual_review_modules: int
    site_address: str | None = None
    customer_contact: str | None = None
    customer_address: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None
    customer_reference: str | None = None
    order_reference: str | None = None
    irradiance: IrradianceSummary | None = None
    equipment: tuple[EquipmentRecord,...] = field(default_factory=tuple)
    provenance: ReportProvenance | None = None
    overview_rgb: ReportImage | None = None
    overview_thermal: ReportImage | None = None
    details: tuple[ModuleReportDetail,...] = field(default_factory=tuple)
    release_status: str = "draft"

    def __post_init__(self) -> None:
        for n,v in (("report_id",self.report_id),("project_id",self.project_id),("customer_name",self.customer_name),("site_name",self.site_name),("inspector",self.inspector)): _text(n,v)
        if not isinstance(self.inspection_started_at,datetime):
            raise ValueError("inspection_started_at must be a datetime")
        if self.inspection_started_at.tzinfo is None:
            raise ValueError("inspection timestamp must be timezone-aware")
        for n,v in (("total_modules",self.total_modules),("conspicuous_modules",self.conspicuous_modules),("manual_review_modules",self.manual_review_modules)):
            if isinstance(v,bool) or not isinstance(v,int) or v < 0: raise ValueError(f"{n} must be a non-negative integer")
        if self.conspicuous_modules > self.total_modules or self.manual_review_modules > self.total_modules:
            raise ValueError("report counts cannot exceed total modules")
        if self.overview_rgb and self.overview_rgb.modality!="rgb": raise ValueError("overview_rgb must be RGB")
        if self.overview_thermal and self.overview_thermal.modality!="thermal": raise ValueError("overview_thermal must be thermal")
        if self.release_status not in {"draft","reviewed","released"}: raise ValueError("invalid release_status")

    @property
    def modules_without_documented_finding(self) -> int:
        return self.total_modules-self.conspicuous_modules
