"""Triage tests are synthetic; no private imagery or GPS is committed."""
import pytest

from mcm_solarcheck.services.flight_overlap_audit import FlightOverlapAudit, ImageTransition
from mcm_solarcheck.services.flight_overlap_triage import triage_flight_overlap


def test_weak_thermal_and_clustered_rgb_are_separate_concerns():
    audit = FlightOverlapAudit(
        (ImageTransition("0015", "0016", 80, 46, 0.575, 3),),
        (ImageTransition("0017", "0018", 10, 6, 0.6, 4),),
        (),
    )
    result = triage_flight_overlap(audit)
    assert len(result.concerns) == 2
    assert result.concerns[0].modality == "RGB"
    assert result.concerns[0].reasons == ("spatially clustered or missing matches",)
    assert result.concerns[1].modality == "Thermal"
    assert result.concerns[1].reasons == ("few verified matches",)
    assert result.requires_manual_review
    assert not result.metric_orthophoto_approved


def test_strong_transitions_do_not_approve_metric_geometry():
    audit = FlightOverlapAudit((ImageTransition("1", "2", 80, 55, .68, 9),), (), ())
    result = triage_flight_overlap(audit)
    assert not result.requires_manual_review
    assert not result.metric_orthophoto_approved


@pytest.mark.parametrize("kwargs", [{"minimum_inliers": 3}, {"minimum_cells": 17}, {"minimum_cells": True}])
def test_invalid_thresholds_fail_closed(kwargs):
    with pytest.raises(ValueError):
        triage_flight_overlap(FlightOverlapAudit((), (), ()), **kwargs)
