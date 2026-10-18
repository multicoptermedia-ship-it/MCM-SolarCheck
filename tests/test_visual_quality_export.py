"""Quality JSON must be explicit about nonmetric limitations and omit source metadata."""
import json
from types import SimpleNamespace

import pytest

from mcm_solarcheck.services.visual_quality_export import (
    projective_quality_json, projective_quality_summary,
)


def _preview(mean=0.5):
    return SimpleNamespace(
        rms_corner_error_px=1.25,
        overlap_quality=SimpleNamespace(
            covered_pixels=100,
            multiply_covered_pixels=80,
            mean_overlap_disagreement=mean,
            max_overlap_disagreement=2.5,
        ),
    )


def test_quality_json_is_parseable_and_never_claims_metric_or_temperature():
    result = json.loads(projective_quality_json(_preview()))
    assert result["schema_version"] == 1
    assert result["preview_only"] is True
    assert result["metric_orthophoto_verified"] is False
    assert result["temperature_calibrated"] is False
    assert result["multiply_covered_pixels"] == 80
    assert result["rms_corner_error_px"] == 1.25
    assert not any("gps" in key or "filename" in key for key in result)


def test_no_overlap_uses_null_not_zero():
    result = projective_quality_summary(_preview(None))
    assert result["mean_overlap_disagreement_0_255"] is None


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1., 256.])
def test_invalid_quality_values_rejected(bad):
    with pytest.raises(ValueError, match="invalid"):
        projective_quality_summary(_preview(bad))
