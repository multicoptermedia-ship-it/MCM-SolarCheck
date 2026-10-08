"""Evidence-image planning for reviewed inspection findings.

This layer records which source images and pixel locations belong to report
evidence. Rendering/cropping is deliberately separate so original imagery stays
immutable and no RGB/Thermal coordinate equivalence is invented.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from mcm_solarcheck.storage.queries import FindingRecord

@dataclass(frozen=True)
class EvidenceImagePlan:
    finding_id:str
    thermal_source:Path
    thermal_pixel:tuple[int,int]
    rgb_source:Path|None=None
    rgb_marker:tuple[float,float]|None=None
    pairing_confidence:float|None=None
    pairing_method:str|None=None
    cross_sensor_status:str|None=None
    transform_error_px:float|None=None
    module_id:str|None=None
    service_location_status:str='module_unresolved'
    def __post_init__(self):
        x,y=self.thermal_pixel
        if x<0 or y<0:raise ValueError('thermal pixel must be non-negative')
        if self.rgb_marker is not None and self.rgb_source is None:raise ValueError('RGB marker requires an RGB source image')
        if self.pairing_confidence is not None and not 0.0<=self.pairing_confidence<=1.0:raise ValueError('pairing confidence must be between 0 and 1')
        expected='module_resolved' if self.module_id is not None and self.module_id.strip() else 'module_unresolved'
        object.__setattr__(self,'service_location_status',expected)

@dataclass(frozen=True)
class EvidenceImageSet:
    plans:tuple[EvidenceImagePlan,...]

def plan_evidence_images(*,finding_id:str,thermal_source:str|Path,pixel_x:int,pixel_y:int,rgb_source:str|Path|None=None,pairing_confidence:float|None=None,pairing_method:str|None=None)->EvidenceImagePlan:
    """Create an immutable evidence plan without guessing RGB pixel coordinates."""
    return EvidenceImagePlan(finding_id=finding_id,thermal_source=Path(thermal_source),thermal_pixel=(pixel_x,pixel_y),rgb_source=Path(rgb_source) if rgb_source else None,rgb_marker=None,pairing_confidence=pairing_confidence,pairing_method=pairing_method)

def plan_evidence_from_record(record:FindingRecord,*,thermal_source:str|Path,rgb_source:str|Path|None=None)->EvidenceImagePlan:
    """Expose an RGB marker only when persisted cross-sensor evidence is validated.

    Assignment must be unambiguous and must have produced the module identity used
    by the finding.  Otherwise the RGB image may still be referenced, but no marker
    is drawn at a potentially misleading position.
    """
    marker_allowed=(record.transform_validated is True and record.cross_sensor_status=='assigned' and record.module_id is not None and record.rgb_pixel_x is not None and record.rgb_pixel_y is not None and rgb_source is not None)
    marker=(record.rgb_pixel_x,record.rgb_pixel_y) if marker_allowed else None
    return EvidenceImagePlan(
        finding_id=record.finding_id,thermal_source=Path(thermal_source),thermal_pixel=(record.pixel_x,record.pixel_y),
        rgb_source=Path(rgb_source) if rgb_source else None,rgb_marker=marker,pairing_confidence=record.pair_confidence,
        pairing_method=record.transform_method,cross_sensor_status=record.cross_sensor_status,
        transform_error_px=record.transform_error_px,module_id=record.module_id,
    )
