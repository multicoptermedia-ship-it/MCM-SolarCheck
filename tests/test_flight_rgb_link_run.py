"""Flight-wide RGB link status tests with synthetic local images."""
import cv2
import numpy as np

from mcm_solarcheck.services.flight_rgb_link_run import check_flight_rgb_links


def test_all_adjacent_links_reported_including_corrupt_image(tmp_path):
    texture = np.random.default_rng(321).integers(0, 256, (240, 320, 3), dtype=np.uint8)
    for index in range(6):
        path = tmp_path / f"DJI_20260725154421_{index:04d}_V.PNG"
        if index == 3:
            path.write_bytes(b"broken")
        else:
            assert cv2.imwrite(str(path), texture)
    result = check_flight_rgb_links(tmp_path, batch_size=4, overlap=2)
    assert result["capture_count"] == 6
    assert result["batch_count"] == 2
    assert len(result["links"]) == 5
    assert result["registered"] + result["failed"] == 5
    assert result["failed"] >= 2
    assert result["links"][2]["status"] == "failed"
    assert result["links"][3]["status"] == "failed"
    assert result["metric_orthophoto_verified"] is False


def test_missing_rgb_is_reported_not_skipped(tmp_path):
    texture = np.random.default_rng(123).integers(0, 256, (240, 320, 3), dtype=np.uint8)
    assert cv2.imwrite(str(tmp_path / "DJI_20260725154421_0001_V.PNG"), texture)
    (tmp_path / "DJI_20260725154421_0002_T.PNG").write_bytes(b"thermal")
    result = check_flight_rgb_links(tmp_path)
    assert len(result["links"]) == 1
    assert result["failed"] == 1
    assert "missing" in result["links"][0]["reason"]
