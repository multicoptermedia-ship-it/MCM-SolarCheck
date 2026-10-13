import pytest

from mcm_solarcheck.services.pv_ai_fault_taxonomy import (
    FaultHypothesis, ObservationKind, PVFaultAssessment,
)
from mcm_solarcheck.services.pv_rgb_training_candidate import RGBTrainingCandidate


def test_all_seven_electrical_hypotheses_available_without_claimed_diagnosis():
    assert len(FaultHypothesis) == 7
    assessment = PVFaultAssessment(ObservationKind.THERMAL_HOTSPOT,
                                   (FaultHypothesis.BYPASS_DIODE_OPEN, FaultHypothesis.PID),
                                   "thermal-frame-12")
    assert assessment.review_status == "suspected"
    assert assessment.requires_followup


def test_visible_rgb_candidate_needs_explicit_consent_and_review():
    args = dict(thermal_finding_id="t1", rgb_frame_id="rgb1",
                registration_reference="verified-map-1",
                rgb_observation=ObservationKind.RGB_GLASS_DAMAGE,
                bbox_xyxy=(0.1, 0.2, 0.3, 0.4), reviewer_id="expert")
    without = RGBTrainingCandidate(**args, training_consent_active=False, consent_reference=None)
    assert not without.eligible_for_training_review
    with_consent = RGBTrainingCandidate(**args, training_consent_active=True,
                                         consent_reference="consent-2026")
    assert with_consent.eligible_for_training_review


def test_invisible_thermal_fault_is_not_fabricated_as_rgb_label():
    candidate = RGBTrainingCandidate("t1", "rgb1", "verified-map-1", None, None,
                                     "expert", True, "consent-2026")
    assert not candidate.eligible_for_training_review


@pytest.mark.parametrize("box", [(-0.1, 0.1, 0.3, 0.4), (0.2, 0.2, 0.1, 0.4),
                                  (0.1, 0.1, float("nan"), 0.5)])
def test_invalid_rgb_bounding_boxes_rejected(box):
    with pytest.raises(ValueError):
        RGBTrainingCandidate("t1", "rgb1", "verified-map-1",
                             ObservationKind.RGB_SOILING, box, "expert", True, "consent")
