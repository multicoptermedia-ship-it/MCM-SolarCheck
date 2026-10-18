"""Regression tests for cooperative flight cancellation and Qt worker signals."""
import pytest
import cv2
import numpy as np
from mcm_solarcheck.services.flight_rgb_link_run import FlightRunCancelled, save_flight_rgb_link_run


def test_cancel_before_first_link_does_not_write_json(tmp_path):
    flight = tmp_path / "flight"
    flight.mkdir()
    pixels = np.random.default_rng(12).integers(0, 256, (200, 260, 3), dtype=np.uint8)
    for index in range(3):
        assert cv2.imwrite(str(flight / f"DJI_20260725154421_{index:04d}_V.PNG"), pixels)
    target = tmp_path / "out.json"
    with pytest.raises(FlightRunCancelled):
        save_flight_rgb_link_run(flight, target, should_cancel=lambda: True)
    assert not target.exists()


def test_cancel_after_first_link_reports_only_completed_link(tmp_path):
    flight = tmp_path / "flight"
    flight.mkdir()
    pixels = np.random.default_rng(22).integers(0, 256, (200, 260, 3), dtype=np.uint8)
    for index in range(3):
        assert cv2.imwrite(str(flight / f"DJI_20260725154421_{index:04d}_V.PNG"), pixels)
    completed = []
    target = tmp_path / "out.json"
    with pytest.raises(FlightRunCancelled):
        save_flight_rgb_link_run(
            flight, target,
            on_progress=lambda done, total, record: completed.append(done),
            should_cancel=lambda: bool(completed),
        )
    assert completed == [1]
    assert not target.exists()


def test_worker_cancel_signal_without_qt_event_loop(tmp_path):
    pytest.importorskip("PySide6")
    from mcm_solarcheck.gui.flight_rgb_worker import FlightRgbWorker
    worker = FlightRgbWorker(str(tmp_path), str(tmp_path / "result.json"))
    cancelled = []
    worker.cancelled.connect(lambda: cancelled.append(True))
    worker.request_cancel()
    assert worker._stop.is_set()
