"""Progress reporting and automatic folder action regression tests."""
import cv2
import numpy as np

from mcm_solarcheck.services.flight_rgb_link_run import save_flight_rgb_link_run


def test_progress_reports_every_link_and_persists_failures(tmp_path):
    flight = tmp_path / "flight"
    flight.mkdir()
    texture = np.random.default_rng(25).integers(0, 256, (240, 320, 3), dtype=np.uint8)
    for index in range(5):
        path = flight / f"DJI_20260725154421_{index:04d}_V.PNG"
        if index == 2:
            path.write_bytes(b"corrupt")
        else:
            assert cv2.imwrite(str(path), texture)
    calls = []
    target = tmp_path / "result.json"
    result = save_flight_rgb_link_run(
        flight, target, batch_size=3, overlap=1,
        on_progress=lambda done, total, record: calls.append((done, total, record["status"]))
    )
    assert [item[0] for item in calls] == [1, 2, 3, 4]
    assert all(item[1] == 4 for item in calls)
    assert result["registered"] + result["failed"] == 4
    assert result["failed"] >= 2
    assert target.is_file()
    assert '"processing_kind": "nonmetric_rgb_link_registration"' in target.read_text()


def test_gui_folder_button_calls_full_flight_handler():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from mcm_solarcheck.gui.import_page import make_import_page
    selected = []
    page = make_import_page(
        current_project_id="pilot", on_run_rgb_links=selected.append,
        choose_rgb_link_folder=lambda: "/tmp/flight",
    )
    button = page.findChild(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton,
                            "run_rgb_links_button")
    assert button is not None and button.isEnabled()
    button.click()
    assert selected == ["/tmp/flight"]
