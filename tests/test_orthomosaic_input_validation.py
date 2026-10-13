import pytest

from mcm_solarcheck.services.orthomosaic_input_validation import (
    ManualCameraAngle, OverlapAssessment, OverlapState, OVERLAP_FAILURE_MESSAGE,
)
from mcm_solarcheck.services.orthomosaic_reconstruction_gate import OrthomosaicPreflight


def test_manual_angle_accepts_perpendicular_and_records_source():
    value = ManualCameraAngle(90.0, "series")
    assert value.source == "user_supplied"


@pytest.mark.parametrize("angle", [-1, 90.01, float("nan"), float("inf")])
def test_invalid_manual_angle(angle):
    with pytest.raises(ValueError):
        ManualCameraAngle(angle, "image")


def test_unknown_overlap_is_not_misreported_as_failure():
    gate = OrthomosaicPreflight(29, OverlapAssessment(OverlapState.UNKNOWN), False)
    assert not gate.can_attempt_reconstruction
    assert "noch nicht geprüft" in gate.user_message


def test_insufficient_overlap_blocks_even_with_angle():
    overlap = OverlapAssessment(OverlapState.INSUFFICIENT, "feature_matches", "audit-42")
    gate = OrthomosaicPreflight(29, overlap, False, ManualCameraAngle(88, "series"))
    assert not gate.can_attempt_reconstruction
    assert gate.user_message == OVERLAP_FAILURE_MESSAGE


def test_sufficient_overlap_still_needs_camera_input():
    overlap = OverlapAssessment(OverlapState.SUFFICIENT, "feature_matches", "audit-43")
    gate = OrthomosaicPreflight(29, overlap, False)
    assert not gate.can_attempt_reconstruction
    assert "Kamerawinkel" in gate.user_message
    assert OrthomosaicPreflight(29, overlap, False, ManualCameraAngle(85, "image")).can_attempt_reconstruction


def test_claimed_overlap_requires_evidence():
    with pytest.raises(ValueError):
        OverlapAssessment(OverlapState.SUFFICIENT)
    with pytest.raises(ValueError):
        OverlapAssessment(OverlapState.UNKNOWN, "guessed", "none")
