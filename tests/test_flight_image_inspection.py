"""All-image inspection tests with synthetic images only."""
import cv2
import numpy as np
from mcm_solarcheck.services.flight_image_inspection import inspect_flight_images


def _image(path):
    ok, encoded = cv2.imencode(".png", np.full((32, 32, 3), 125, dtype=np.uint8))
    assert ok
    path.write_bytes(encoded.tobytes())


def test_all_images_get_individual_status_and_missing_thermal(tmp_path):
    for i in range(1, 6):
        _image(tmp_path / f"DJI_20260725154421_{i:04d}_V.PNG")
        if i != 5:
            _image(tmp_path / f"DJI_20260725154421_{i:04d}_T.PNG")
    (tmp_path / "DJI_20260725154421_0003_T.PNG").write_bytes(b"invalid")
    (tmp_path / "notes.txt").write_text("ignored")
    report = inspect_flight_images(tmp_path)
    assert report["captures"] == 5
    assert len(report["images"]) == 10
    assert report["readable"] == 8
    assert report["unreadable"] == 1
    assert report["missing"] == 1
    assert report["ignored"] == ["notes.txt"]


def test_oversized_image_is_explicit(tmp_path):
    _image(tmp_path / "DJI_20260725154421_0001_V.PNG")
    report = inspect_flight_images(tmp_path, max_image_bytes=8)
    assert report["oversized"] == 1
    assert report["missing"] == 1


def test_native_dimensions_and_json_artifact_do_not_change_sources(tmp_path):
    import json
    import pytest
    from mcm_solarcheck.services.flight_image_inspection import save_flight_inspection

    rgb = tmp_path / "DJI_20260725154421_0001_V.PNG"
    thermal = tmp_path / "DJI_20260725154421_0001_T.PNG"
    _image(rgb)
    _image(thermal)
    original = (rgb.read_bytes(), thermal.read_bytes())
    destination = tmp_path / "inspection.json"
    report = save_flight_inspection(tmp_path, destination)
    assert [(item["width"], item["height"]) for item in report["images"]] == [
        (32, 32), (32, 32)
    ]
    assert (rgb.read_bytes(), thermal.read_bytes()) == original
    saved = json.loads(destination.read_text(encoding="utf-8"))
    assert saved["original_resolution_preserved"] is True
    assert saved["metric_orthophoto_verified"] is False
    assert saved["temperature_calibrated"] is False
    with pytest.raises(ValueError, match="new JSON"):
        save_flight_inspection(tmp_path, destination)
