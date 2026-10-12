import pytest

from mcm_solarcheck.services.pv_detector_license_gate import (
    DetectorFamily, DetectorLicenseReview, require_proprietary_detector_license,
)
from mcm_solarcheck.services.pv_training_detector_approval import authorize_detector_training_metadata
from mcm_solarcheck.services.pv_training_approval_snapshot import TrainingApprovalSnapshot
from mcm_solarcheck.services.pv_yolo_training_plan import YoloTrainingPlan


def _review(family=DetectorFamily.RT_DETR, approved=True, enterprise=None):
    return DetectorLicenseReview(family, "Apache-2.0", "reviewed-weights",
                                 "human-reviewer", "weight-license-1",
                                 approved, enterprise)


def _snapshot():
    plan = YoloTrainingPlan("a" * 64, "dataset", "thermal", ("thermal_hotspot",),
                            42, 50, 640, 8, "local-model", "weight-license-1")
    return TrainingApprovalSnapshot("a" * 64, "b" * 64, "c" * 64, plan)


def test_permissive_candidate_requires_explicit_human_approval():
    assert authorize_detector_training_metadata(_snapshot(), _review()).status == "authorized_metadata_only_no_training"
    with pytest.raises(PermissionError):
        require_proprietary_detector_license(_review(approved=False))


def test_ultralytics_proprietary_without_enterprise_rejected():
    with pytest.raises(PermissionError):
        _review(DetectorFamily.ULTRALYTICS_YOLO)
    assert _review(DetectorFamily.ULTRALYTICS_YOLO, enterprise="enterprise-contract").proprietary_use_approved


def test_unknown_model_family_rejected():
    with pytest.raises(PermissionError):
        _review(DetectorFamily.OTHER)


def test_model_license_evidence_must_match_training_plan():
    review = DetectorLicenseReview(DetectorFamily.RT_DETR, "Apache-2.0", "weights",
                                   "reviewer", "other-evidence", True)
    with pytest.raises(PermissionError):
        authorize_detector_training_metadata(_snapshot(), review)


def test_wrong_code_license_rejected():
    with pytest.raises(PermissionError):
        DetectorLicenseReview(DetectorFamily.RT_DETR, "AGPL-3.0", "weights",
                              "reviewer", "evidence", True)
