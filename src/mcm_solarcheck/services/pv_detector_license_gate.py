"""Fail-closed license decision for proprietary PV detector training."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DetectorFamily(str, Enum):
    ULTRALYTICS_YOLO = "ultralytics_yolo"
    RT_DETR = "rt_detr"
    OTHER = "other"


@dataclass(frozen=True)
class DetectorLicenseReview:
    family: DetectorFamily
    code_license: str
    weights_license: str
    reviewer: str
    evidence_reference: str
    proprietary_use_approved: bool
    enterprise_license_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.family, DetectorFamily):
            raise ValueError("recognized detector family required")
        if any(not isinstance(x, str) or not x.strip() for x in
               (self.code_license, self.weights_license, self.reviewer, self.evidence_reference)):
            raise ValueError("human code and weights license review required")
        if self.proprietary_use_approved and self.family is DetectorFamily.ULTRALYTICS_YOLO:
            if not self.enterprise_license_reference or not self.enterprise_license_reference.strip():
                raise PermissionError("proprietary Ultralytics use requires enterprise license evidence")
        if self.proprietary_use_approved and self.family is DetectorFamily.RT_DETR:
            if self.code_license.strip().lower() != "apache-2.0":
                raise PermissionError("RT-DETR code license mismatch")
        if self.proprietary_use_approved and self.family is DetectorFamily.OTHER:
            raise PermissionError("unknown detector cannot be automatically approved")


def require_proprietary_detector_license(review: DetectorLicenseReview) -> None:
    if not isinstance(review, DetectorLicenseReview) or not review.proprietary_use_approved:
        raise PermissionError("proprietary detector training not licensed")
    # Human-reviewed weights and dependency rights are separate from code rights.
