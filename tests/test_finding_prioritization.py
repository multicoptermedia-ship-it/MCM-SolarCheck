from mcm_solarcheck.domain.models import Finding
from mcm_solarcheck.review.prioritization import prioritize_finding


def finding(**changes):
    values=dict(finding_id="F-1",thermal_frame_id="T-1",pixel_x=10,pixel_y=20)
    values.update(changes)
    return Finding(**values)


def test_raw_radiometric_values_never_become_severity():
    result=prioritize_finding(finding(raw_value=22000,raw_delta_from_median=1500))
    assert result.level=="unrated"
    assert result.score is None
    assert result.reason=="calibrated_temperature_required"


def test_nonfinite_temperature_fails_closed():
    result=prioritize_finding(finding(temperature_c=float("nan"),confidence=.9))
    assert result.level=="unrated"
    assert result.reason=="invalid_temperature"


def test_missing_confidence_remains_unrated():
    result=prioritize_finding(finding(temperature_c=55.0))
    assert result.level=="unrated"
    assert result.reason=="confidence_required"


def test_invalid_confidence_fails_closed():
    result=prioritize_finding(finding(temperature_c=55.0,confidence=1.1))
    assert result.level=="unrated"
    assert result.reason=="invalid_confidence"


def test_calibrated_evidence_is_review_priority_not_defect_severity():
    result=prioritize_finding(finding(temperature_c=55.0,confidence=.8))
    assert result.level=="review"
    assert result.score==.8
    assert result.reason=="calibrated_evidence_available"
