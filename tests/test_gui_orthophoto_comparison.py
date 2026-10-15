"""Desktop comparison slider regression tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QLabel, QSlider

from mcm_solarcheck.gui.orthophoto_comparison import OrthophotoComparisonWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_slider_displays_two_aligned_layers_without_changing_arrays(qapp):
    rgb = np.full((4, 5, 3), 30, dtype=np.uint8)
    thermal = np.full((4, 5), 42, dtype=np.float32)
    thermal[:, 0] = np.nan
    original_rgb = rgb.copy()
    original_thermal = thermal.copy()
    widget = OrthophotoComparisonWidget(rgb, thermal)
    slider = widget.findChild(QSlider, "orthophoto_thermal_opacity_slider")
    label = widget.findChild(QLabel, "orthophoto_comparison_image")
    assert slider.minimum() == 0 and slider.maximum() == 100
    assert not label.pixmap().isNull()
    slider.setValue(100)
    assert not label.pixmap().isNull()
    slider.setValue(0)
    assert np.array_equal(rgb, original_rgb)
    assert np.array_equal(thermal, original_thermal, equal_nan=True)


def test_widget_rejects_unaligned_layers(qapp):
    with pytest.raises(ValueError, match="match"):
        OrthophotoComparisonWidget(
            np.zeros((3, 4, 3), dtype=np.uint8),
            np.zeros((4, 3), dtype=np.float32),
        )


def test_import_comparison_requires_project_and_two_files(qapp):
    from PySide6.QtWidgets import QPushButton
    from mcm_solarcheck.gui.import_page import make_import_page

    disabled = make_import_page()
    assert not disabled.findChild(QPushButton, "compare_orthophotos_button").isEnabled()
    calls = []
    page = make_import_page(
        current_project_id="P1",
        on_compare_orthophotos=lambda rgb, thermal: calls.append((rgb, thermal)),
        choose_orthophoto_pair=lambda: ("/data/rgb.tif", "/data/thermal.tif"),
    )
    page.findChild(QPushButton, "compare_orthophotos_button").click()
    assert calls == [("/data/rgb.tif", "/data/thermal.tif")]


def test_import_comparison_cancel_does_not_invoke_callback(qapp):
    from PySide6.QtWidgets import QPushButton
    from mcm_solarcheck.gui.import_page import make_import_page

    calls = []
    page = make_import_page(
        current_project_id="P1",
        on_compare_orthophotos=lambda *paths: calls.append(paths),
        choose_orthophoto_pair=lambda: ("/data/rgb.tif", ""),
    )
    page.findChild(QPushButton, "compare_orthophotos_button").click()
    assert calls == []


def test_desktop_comparison_shows_slider_and_resets_on_project_change(tmp_path, qapp):
    import rasterio
    from rasterio.transform import from_origin
    from PySide6.QtWidgets import QSlider, QLabel
    from mcm_solarcheck.offline.composition import build_offline_services
    from mcm_solarcheck.gui.shell import SolarCheckMainWindow
    from mcm_solarcheck.services.deployment import DeploymentMode
    from mcm_solarcheck.services.shell_navigation import ShellRoute

    service = build_offline_services(tmp_path / "projects.sqlite").projects
    service.create_project("P1", "First")
    service.create_project("P2", "Second")
    rgb = tmp_path / "rgb.tif"
    thermal = tmp_path / "thermal.tif"
    for path, values in (
        (rgb, np.zeros((3, 4, 4), dtype=np.uint8)),
        (thermal, np.full((1, 4, 4), 42, dtype=np.float32)),
    ):
        with rasterio.open(
            path, "w", driver="GTiff", width=4, height=4,
            count=values.shape[0], dtype=values.dtype, crs="EPSG:25832",
            transform=from_origin(350000, 5650000, 1, 1),
        ) as dataset:
            dataset.write(values)
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    window._open_project("P1")
    before = service.state("P1")
    window._compare_project_orthophotos(str(rgb), str(thermal))
    page = window._pages[ShellRoute.IMPORT]
    slider = page.findChild(QSlider, "orthophoto_thermal_opacity_slider")
    assert slider is not None and slider.value() == 50
    slider.setValue(90)
    assert service.state("P1") == before
    window._open_project("P2")
    assert window._pages[ShellRoute.IMPORT].findChild(
        QSlider, "orthophoto_thermal_opacity_slider"
    ) is None
    window._compare_project_orthophotos(str(rgb), str(rgb))
    error = window._pages[ShellRoute.IMPORT].findChild(QLabel, "orthophoto_comparison_error")
    assert error is not None and "fehlgeschlagen" in error.text()


def test_zoom_buttons_scale_both_layers_in_one_viewport(qapp):
    from PySide6.QtWidgets import QPushButton, QScrollArea
    widget = OrthophotoComparisonWidget(
        np.zeros((40, 60, 3), dtype=np.uint8),
        np.ones((40, 60), dtype=np.float32),
    )
    label = widget.findChild(QLabel, 'orthophoto_comparison_image')
    viewport = widget.findChild(QScrollArea, 'orthophoto_comparison_scroll_area')
    assert viewport.widget() is label
    original = label.pixmap().size()
    widget.findChild(QPushButton, 'orthophoto_zoom_in').click()
    assert label.pixmap().width() > original.width()
    widget.findChild(QSlider, 'orthophoto_thermal_opacity_slider').setValue(100)
    assert label.pixmap().width() > original.width()
    widget.findChild(QPushButton, 'orthophoto_zoom_reset').click()
    assert label.pixmap().size() == original
