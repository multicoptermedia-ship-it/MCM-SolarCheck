"""Reviewed PDF handoff from a non-metric PNG and local quality JSON."""
import json

import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
from mcm_solarcheck.services.visual_preview_report_export import (
    export_reviewed_pdf_with_visual_preview,
)


def _inputs(tmp_path):
    png = tmp_path / "preview.png"
    Image.fromarray(np.full((140, 200, 3), 127, dtype=np.uint8)).save(png)
    quality = tmp_path / "quality.json"
    quality.write_text(json.dumps({
        "schema_version": 1, "preview_only": True,
        "metric_orthophoto_verified": False, "temperature_calibrated": False,
        "rms_corner_error_px": 0.2, "covered_pixels": 28000,
        "multiply_covered_pixels": 25000,
        "mean_overlap_disagreement_0_255": 0.0,
        "max_overlap_disagreement_0_255": 0.0,
    }), encoding="utf-8")
    return png, quality


def test_nonmetric_preview_reaches_real_reviewed_pdf(tmp_path):
    png, quality = _inputs(tmp_path)
    destination = tmp_path / "reviewed.pdf"
    result = export_reviewed_pdf_with_visual_preview(
        fictional_pilot_report(), png, quality, destination)
    assert result == destination
    assert destination.read_bytes().startswith(b"%PDF")
    assert destination.stat().st_size > 1000


def test_report_rejects_unreviewed_object_and_false_metric_flag(tmp_path):
    png, quality = _inputs(tmp_path)
    destination = tmp_path / "reviewed.pdf"
    with pytest.raises(TypeError, match="reviewed"):
        export_reviewed_pdf_with_visual_preview(object(), png, quality, destination)
    record = json.loads(quality.read_text(encoding="utf-8"))
    record["metric_orthophoto_verified"] = True
    quality.write_text(json.dumps(record), encoding="utf-8")
    with pytest.raises(ValueError, match="non-metric"):
        export_reviewed_pdf_with_visual_preview(
            fictional_pilot_report(), png, quality, destination)
    assert not destination.exists()


def test_report_never_overwrites_existing_pdf(tmp_path):
    png, quality = _inputs(tmp_path)
    destination = tmp_path / "reviewed.pdf"
    destination.write_bytes(b"existing")
    with pytest.raises(ValueError, match="new PDF"):
        export_reviewed_pdf_with_visual_preview(
            fictional_pilot_report(), png, quality, destination)
    assert destination.read_bytes() == b"existing"
