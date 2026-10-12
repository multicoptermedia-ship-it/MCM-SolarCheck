import pytest

from mcm_solarcheck.services.pv_dataset_intake import LicenseDecision
from mcm_solarcheck.services.pv_detector_backend_contract import (
    DetectionBox, DetectorManifest, require_licensed_detector_manifest,
)
from mcm_solarcheck.services.pv_detector_license_gate import DetectorFamily, DetectorLicenseReview
from mcm_solarcheck.services.pv_thermal_dataset_shortlist import (
    THERMAL_CANDIDATES, require_reviewed_thermal_dataset,
)


def test_normalized_detection_box():
    assert DetectionBox(0, 0.8, 0.1, 0.2, 0.4, 0.5).confidence == 0.8
    for values in ((0, 1.1, 0, 0, 1, 1), (0, 0.5, 0.8, 0, 0.2, 1),
                   (-1, 0.5, 0, 0, 1, 1), (0, float("nan"), 0, 0, 1, 1)):
        with pytest.raises(ValueError):
            DetectionBox(*values)


def test_manifest_requires_matching_human_license_review():
    manifest = DetectorManifest(DetectorFamily.RT_DETR, "model-sha256", ("hotspot",), "evidence")
    review = DetectorLicenseReview(DetectorFamily.RT_DETR, "Apache-2.0", "reviewed weights",
                                   "reviewer", "evidence", True)
    require_licensed_detector_manifest(manifest, review)
    with pytest.raises(PermissionError):
        require_licensed_detector_manifest(manifest, DetectorLicenseReview(
            DetectorFamily.RT_DETR, "Apache-2.0", "reviewed weights",
            "reviewer", "different", True))


def test_thermal_candidate_is_never_automatically_approved():
    record = THERMAL_CANDIDATES[0].to_unreviewed_record()
    assert record.decision is LicenseDecision.UNREVIEWED
    with pytest.raises(PermissionError):
        require_reviewed_thermal_dataset(record)
