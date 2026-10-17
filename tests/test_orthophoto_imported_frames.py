"""Importer bridge guards for native planar orthophoto generation."""
import numpy as np
import cv2
import pytest

from mcm_solarcheck.domain.models import ImageFrame, ThermalFrame
from mcm_solarcheck.services.orthophoto_imported_frames import (
    ImportedSurveyedControl, surveyed_frames_from_import,
)

POINTS = ((0., 0.), (7., 0.), (7., 7.), (0., 7.))


def test_imported_rgb_and_thermal_frames_are_separated(tmp_path):
    path = tmp_path / "frame.png"
    assert cv2.imwrite(str(path), np.zeros((8, 8, 3), dtype=np.uint8))
    frame = ImageFrame("rgb-1", path, width=8, height=8)
    control = ImportedSurveyedControl("rgb-1", POINTS, POINTS, independently_surveyed=True)
    surveyed = surveyed_frames_from_import((frame,), (control,))
    assert surveyed[0].image_path == path
    assert surveyed[0].controls_surveyed
    with pytest.raises(ValueError, match="separately"):
        surveyed_frames_from_import((ThermalFrame("thermal-1", path, width=8, height=8),),
                                    (ImportedSurveyedControl("thermal-1", POINTS, POINTS, True),))


def test_reject_missing_survey_and_out_of_image_controls(tmp_path):
    path = tmp_path / "rgb.png"
    assert cv2.imwrite(str(path), np.zeros((8, 8, 3), dtype=np.uint8))
    frame = ImageFrame("rgb", path, width=8, height=8)
    with pytest.raises(ValueError, match="independently"):
        surveyed_frames_from_import((frame,), (ImportedSurveyedControl("rgb", POINTS, POINTS),))
    outside = ((0., 0.), (8., 0.), (7., 7.), (0., 7.))
    with pytest.raises(ValueError, match="outside"):
        surveyed_frames_from_import((frame,), (ImportedSurveyedControl("rgb", outside, POINTS, True),))


def test_raw_thermal_uint16_is_accepted_and_palette_rejected(tmp_path):
    raw = tmp_path / "raw.png"
    assert cv2.imwrite(str(raw), np.full((8, 8), 2048, dtype=np.uint16))
    frame = ThermalFrame("thermal", raw, width=8, height=8)
    control = ImportedSurveyedControl("thermal", POINTS, POINTS, True)
    assert surveyed_frames_from_import((frame,), (control,), thermal=True)[0].image_path == raw
    palette = tmp_path / "palette.png"
    assert cv2.imwrite(str(palette), np.zeros((8, 8, 3), dtype=np.uint8))
    frame.source_file = palette
    with pytest.raises(ValueError, match="single-band"):
        surveyed_frames_from_import((frame,), (control,), thermal=True)


def test_reject_source_dimension_mismatch(tmp_path):
    path = tmp_path / "rgb.png"
    assert cv2.imwrite(str(path), np.zeros((7, 8, 3), dtype=np.uint8))
    frame = ImageFrame("rgb", path, width=8, height=8)
    with pytest.raises(ValueError, match="dimensions"):
        surveyed_frames_from_import((frame,), (ImportedSurveyedControl("rgb", POINTS, POINTS, True),))
