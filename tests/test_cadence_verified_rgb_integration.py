"""Existing cadence detector can work on SHA-authenticated in-memory BGR.

Tests use synthetic matrices and artificial lattice evidence; never claim
a real PV module or access DJI private source photographs.
"""
from __future__ import annotations

import numpy as np
import pytest

from mcm_solarcheck.vision.cadence_module_detector import (
    CadenceConfirmedModuleDetector,
)
from mcm_solarcheck.vision.cadence_gate import CadenceGateResult
from mcm_solarcheck.vision.detection import ModuleDetection
from mcm_solarcheck.vision.grid_cadence import GridCadence


def test_array_path_never_reopens_image_file(monkeypatch):
    import mcm_solarcheck.vision.cadence_module_detector as module

    detector = CadenceConfirmedModuleDetector()
    monkeypatch.setattr(
        module.cv2, "imread",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no path read")),
    )
    monkeypatch.setattr(
        detector.image_detector, "detect",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("no file detector")),
    )
    support = ModuleDetection(((10, 10), (40, 10), (40, 30), (10, 30)), .9)
    monkeypatch.setattr(
        detector.image_detector, "detect_array",
        lambda bgr: (support,),
    )
    monkeypatch.setattr(module, "detect_structural_lines", lambda *a, **kw: ())
    monkeypatch.setattr(module, "extract_grid_line_families", lambda lines: ())
    monkeypatch.setattr(
        module, "assess_ambiguous_module_cadence",
        lambda *_a, **_kw: CadenceGateResult(
            False, (), "two_grid_families_required",
        ),
    )
    image = np.zeros((80, 100, 3), dtype=np.uint8)
    candidates, reason = detector.detect_array_with_status(image)
    assert candidates == ()
    assert reason == "two_grid_families_required"
    assert detector.detect_array(image) == ()


def test_in_memory_cadence_still_requires_spatial_image_support(monkeypatch):
    import mcm_solarcheck.vision.cadence_module_detector as module

    detector = CadenceConfirmedModuleDetector(minimum_iou=.30)
    cell = ModuleDetection(((10, 10), (40, 10), (40, 30), (10, 30)), .8)
    support = ModuleDetection(((12, 11), (38, 11), (38, 29), (12, 29)), .8)
    image = np.zeros((80, 100, 3), dtype=np.uint8)
    monkeypatch.setattr(module, "detect_structural_lines", lambda *a, **k: ())
    # The simulated accepted cadence must have two independent grid axes.
    # An empty-family fixture would correctly fail the detector's axis gate.
    monkeypatch.setattr(
        module, "extract_grid_line_families",
        lambda lines: (object(), object()),
    )
    axes = (
        GridCadence(True, "synthetic", 10.0, 2),
        GridCadence(True, "synthetic", 10.0, 2),
    )
    passed_iou = []
    def gate(*_a, minimum_iou, **_k):
        passed_iou.append(minimum_iou)
        return CadenceGateResult(True, axes, "accepted", (0, 0))
    monkeypatch.setattr(module, "assess_ambiguous_module_cadence", gate)
    monkeypatch.setattr(module, "cadence_line_subsets", lambda *_: ((),))
    monkeypatch.setattr(module, "grid_module_detections", lambda *_a, **_k: (cell,))
    monkeypatch.setattr(
        module, "filter_cells_by_finite_support",
        lambda cells, *_a: cells,
    )
    monkeypatch.setattr(
        detector.image_detector, "detect_array",
        lambda bgr: (support,),
    )
    found, reason = detector.detect_array_with_status(image)
    assert len(found) == 1 and reason == "spatially_supported"
    assert found[0].polygon_px == cell.polygon_px
    assert passed_iou == [.30]

    # The same artificial grid MUST be rejected without independent image
    # evidence, even if a faulty upstream gate claimed acceptance.
    monkeypatch.setattr(detector.image_detector, "detect_array", lambda bgr: ())
    found, reason = detector.detect_array_with_status(image)
    assert found == () and reason == "no_spatial_overlap"


@pytest.mark.parametrize("invalid", [
    None, np.zeros((0, 100, 3), dtype=np.uint8),
    np.zeros((50, 50), dtype=np.uint8),
    np.zeros((50, 50, 4), dtype=np.uint8),
    np.zeros((50, 50, 3), dtype=np.float32),
])
def test_untrusted_array_shapes_are_rejected_without_any_detection(invalid):
    detector = CadenceConfirmedModuleDetector()
    assert detector.detect_array_with_status(invalid) == (
        (), "invalid_bgr_image",
    )


def test_invalid_config_is_rejected_before_array_detection(monkeypatch):
    detector = CadenceConfirmedModuleDetector(minimum_iou=float("nan"))
    monkeypatch.setattr(
        detector.image_detector, "detect_array",
        lambda *_: (_ for _ in ()).throw(AssertionError("never detect")),
    )
    assert detector.detect_array_with_status(np.zeros((5, 5, 3), dtype=np.uint8)) == (
        (), "invalid_detector_configuration",
    )
