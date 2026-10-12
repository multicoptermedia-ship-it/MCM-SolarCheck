"""Combine dataset snapshot with explicit model licensing; no model execution."""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.pv_detector_license_gate import (
    DetectorLicenseReview, require_proprietary_detector_license,
)
from mcm_solarcheck.services.pv_training_approval_snapshot import TrainingApprovalSnapshot


@dataclass(frozen=True)
class DetectorTrainingAuthorization:
    dataset_sha256: str
    detector_family: str
    model_reference: str
    license_evidence: str
    status: str = "authorized_metadata_only_no_training"


def authorize_detector_training_metadata(
    snapshot: TrainingApprovalSnapshot,
    review: DetectorLicenseReview,
) -> DetectorTrainingAuthorization:
    if not isinstance(snapshot, TrainingApprovalSnapshot) or snapshot.status != "approved_metadata_only":
        raise PermissionError("approved dataset metadata required")
    if snapshot.plan.status != "plan_only_no_training" or snapshot.plan.dataset_sha256 != snapshot.dataset_sha256:
        raise PermissionError("invalid dataset training plan")
    require_proprietary_detector_license(review)
    if snapshot.plan.weights_license_review_reference != review.evidence_reference:
        raise PermissionError("training plan and detector license evidence mismatch")
    return DetectorTrainingAuthorization(
        snapshot.dataset_sha256, review.family.value,
        snapshot.plan.model_reference, review.evidence_reference,
    )
