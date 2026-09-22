from pathlib import Path

import pytest

from mcm_solarcheck.importers.m3t_rgb import M3TRGBImporter, _jpeg_dimensions
from mcm_solarcheck.vision.detection import ModuleDetection, normalize_module_detections


def test_rgb_frame_id_uses_visible_sequence():
    path = Path("DJI_20250825121338_0001_V.JPG")
    assert M3TRGBImporter.frame_id(path) == "V-0001"


def test_jpeg_dimension_reader_handles_sof0():
    # SOI + SOF0(length=17, precision=8, height=3000, width=4000, 3 components)
    data = b"\xff\xd8\xff\xc0\x00\x11\x08\x0b\xb8\x0f\xa0" + b"\x00" * 10
    assert _jpeg_dimensions(data) == (4000, 3000)


def test_detection_validation_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        ModuleDetection(((0, 0), (10, 0), (10, 10)), 1.2)


def test_normalization_filters_orders_and_numbers_modules():
    detections = (
        ModuleDetection(((100, 100), (150, 100), (150, 150), (100, 150)), 0.95),
        ModuleDetection(((10, 10), (60, 10), (60, 60), (10, 60)), 0.90),
        ModuleDetection(((200, 10), (250, 10), (250, 60), (200, 60)), 0.20),
        ModuleDetection(((300, 10), (350, 10), (350, 60), (300, 60)), 0.99, "roof"),
    )
    modules = normalize_module_detections("T-0042", detections, detector_name="fixture", minimum_confidence=0.5, image_size=(4000,3000))
    assert [m.module_id for m in modules] == ["T-0042:M-0001", "T-0042:M-0002"]
    assert modules[0].polygon_px[0] == (10, 10)
    assert modules[1].detection_confidence == 0.95


def test_normalization_geometry_gate_rejects_duplicate_and_outside():
    good = ModuleDetection(((100,100),(300,100),(300,500),(100,500)), .95)
    duplicate = ModuleDetection(((105,105),(305,105),(305,505),(105,505)), .80)
    outside = ModuleDetection(((-10,100),(200,100),(200,500),(-10,500)), .99)
    modules = normalize_module_detections("V-1",(duplicate,outside,good),detector_name="fixture",image_size=(4000,3000))
    assert len(modules)==1
    assert modules[0].detection_confidence==.95


def test_normalization_requires_image_size_for_safe_default():
    with pytest.raises(ValueError):
        normalize_module_detections("V-1",(ModuleDetection(((0,0),(10,0),(10,10)),.9),),detector_name="fixture")
