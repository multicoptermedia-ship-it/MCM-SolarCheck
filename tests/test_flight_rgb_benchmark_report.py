"""Benchmark reports expose only resource estimates, not local image paths."""
import cv2
import numpy as np

from mcm_solarcheck.services.flight_rgb_benchmark_report import prepare_rgb_benchmark_report


def test_anonymous_report_omits_customer_file_names(tmp_path):
    source = tmp_path / "PRIVATE-CUSTOMER-CAPTURE.jpg"
    assert cv2.imwrite(str(source), np.zeros((4, 5, 3), dtype=np.uint8))
    report = prepare_rgb_benchmark_report([source])
    assert report["frame_count"] == 1
    assert report["estimated_working_disk_bytes"] == 4 * 5 * 3 + 4096
    assert report["measured_peak_rss_bytes"] is None
    assert report["estimate_only"]
    assert "PRIVATE-CUSTOMER-CAPTURE" not in str(report)
