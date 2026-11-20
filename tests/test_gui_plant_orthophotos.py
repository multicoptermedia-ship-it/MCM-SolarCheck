"""VERT-01A: local pair import -> central overview -> SQLite reopen.

All rasters and projects in this module are synthetic and temporary.
"""
import hashlib
import os
import socket

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin
from PySide6.QtWidgets import QApplication, QComboBox, QFileDialog, QLabel, QPushButton, QSlider, QTabWidget

from mcm_solarcheck.gui.shell import SolarCheckMainWindow
from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services.deployment import DeploymentMode
from mcm_solarcheck.services.shell_navigation import ShellRoute


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("offline orthophoto overview must not access the network")
    monkeypatch.setattr(socket, "create_connection", forbidden)


def sources(tmp_path, name, *, visual=False, rgb_value=40):
    rgb = tmp_path / f"{name}-rgb.tif"
    thermal = tmp_path / f"{name}-thermal.tif"
    rgb_values = np.full((4, 24, 32), rgb_value, np.uint8)
    rgb_values[3] = 255
    rgb_values[3, -1] = 0
    if visual:
        thermal_values = np.stack([
            np.full((12, 16), v, np.uint8) for v in (12, 100, 200, 255)
        ])
        thermal_values[3, :, 0] = 0
    else:
        thermal_values = np.full((1, 12, 16), 12000., np.float32)
        thermal_values[:, :, 0] = np.nan
    for path, values, pixel_size in ((rgb, rgb_values, .1), (thermal, thermal_values, .2)):
        with rasterio.open(
            path, "w", driver="GTiff", width=values.shape[2], height=values.shape[1],
            count=len(values), dtype=values.dtype, crs="EPSG:25832",
            transform=from_origin(300000., 5600000., pixel_size, pixel_size),
            nodata=np.nan if values.dtype == np.float32 else None,
        ) as dataset:
            dataset.write(values)
            if len(values) == 4:
                dataset.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue, ColorInterp.alpha)
    return rgb, thermal


def offline_window(database):
    service = build_offline_services(database).projects
    return SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)


def overview(window):
    return window._pages[ShellRoute.PLANT_OVERVIEW]


@pytest.mark.parametrize("visual", (False, True))
def test_import_overview_masks_zoom_project_switch_and_reopen(tmp_path, qapp, monkeypatch, visual):
    database = tmp_path / "projects.sqlite"
    rgb, thermal = sources(tmp_path, "pair", visual=visual)
    original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)}
    window = offline_window(database)
    service = window._project_service
    service.create_project("P1", "First")
    service.create_project("P2", "Empty")
    before = service.state("P1")
    try:
        window._open_project("P1")
        assert overview(window).findChild(QLabel, "plant_orthophoto_empty_state") is not None
        import_page = window._pages[ShellRoute.IMPORT]
        monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([], ""))
        import_page.findChild(QPushButton, "register_orthophoto_pair_button").click()
        assert service.project_orthophoto_pairs("P1") == ()
        assert overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider") is None
        paths = iter((str(rgb), str(thermal)))
        monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([path] if (path := next(paths)) else [], ""))
        kinds = import_page.findChild(QComboBox, "orthophoto_thermal_value_kind")
        kinds.setCurrentIndex(kinds.findData("visual" if visual else "sensor_values"))
        import_page.findChild(QPushButton, "register_orthophoto_pair_button").click()
        window._workflow_navigation.button(ShellRoute.PLANT_OVERVIEW).click()
        page = overview(window)
        assert window.current_route is ShellRoute.PLANT_OVERVIEW
        assert page.findChild(QTabWidget, "plant_overview_tabs").currentIndex() == 0
        assert page.findChild(QComboBox, "plant_orthophoto_pairs").count() == 1
        slider = page.findChild(QSlider, "orthophoto_thermal_opacity_slider")
        image_label = page.findChild(QLabel, "orthophoto_comparison_image")
        slider.setValue(0)
        image = image_label.pixmap().toImage()
        assert image.pixelColor(4, 4).getRgb() == (40, 40, 40, 255)
        slider.setValue(100)
        image = image_label.pixmap().toImage()
        assert image.pixelColor(0, 4).getRgb() == (40, 40, 40, 255)  # masked thermal
        assert image.pixelColor(4, 23).getRgb() == (0, 0, 0, 255)  # masked RGB
        expected = (12, 100, 200, 255) if visual else (128, 127, 0, 255)
        assert image.pixelColor(4, 4).getRgb() == expected
        page.findChild(QPushButton, "orthophoto_zoom_in").click()
        assert image_label.pixmap().width() == 40
        page.findChild(QPushButton, "orthophoto_zoom_reset").click()
        assert image_label.pixmap().width() == 32
        assert service.state("P1") == before
        assert service.project_orthophoto_pairs("P1")[0]['inspection_status'] == "metadata_only"
        # An unsaved import comparison must never replace this registered pair.
        transient = sources(tmp_path, "unsaved", rgb_value=200)
        window._compare_project_orthophotos(*(str(path) for path in transient))
        assert window._orthophoto_comparison is not None
        slider.setValue(0)
        assert image_label.pixmap().toImage().pixelColor(4, 4).getRgb() == (40, 40, 40, 255)
        window._open_project("P2")
        assert overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider") is None
        assert overview(window).findChild(QComboBox, "plant_orthophoto_pairs") is None
    finally:
        window.close()

    reopened = offline_window(database)
    try:
        reopened._open_project("P1")
        reopened.show_route(ShellRoute.PLANT_OVERVIEW)
        page = overview(reopened)
        assert page.findChild(QComboBox, "plant_orthophoto_pairs").count() == 1
        assert page.findChild(QSlider, "orthophoto_thermal_opacity_slider") is not None
        assert reopened._project_service.state("P1") == before
        assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)} == original
    finally:
        reopened.close()


def test_pair_selection_is_project_scoped_and_preserved_during_inventory_refresh(tmp_path, qapp):
    window = offline_window(tmp_path / "projects.sqlite")
    service = window._project_service
    service.create_project("P1", "First")
    service.create_project("P2", "Second")
    try:
        pairs = [service.register_project_orthophoto_pair("P1", *sources(tmp_path, name, rgb_value=value))
                 for name, value in (("a", 40), ("b", 80))]
        foreign = service.register_project_orthophoto_pair("P2", *sources(tmp_path, "c", rgb_value=160))
        window._open_project("P1")
        selector = overview(window).findChild(QComboBox, "plant_orthophoto_pairs")
        # Deliberately choose a pair different from the initial default.
        selected_id = next(p['pair_id'] for p in pairs if p['pair_id'] != selector.currentData())
        selector.setCurrentIndex(selector.findData(selected_id))
        assert overview(window).findChild(QComboBox, "plant_orthophoto_pairs").currentData() == selected_id
        tabs = overview(window).findChild(QTabWidget, "plant_overview_tabs")
        tabs.setCurrentIndex(1)
        overview(window).findChild(QPushButton, "refresh_plant_overview").click()
        assert overview(window).findChild(QTabWidget, "plant_overview_tabs").currentIndex() == 1
        assert overview(window).findChild(QComboBox, "plant_orthophoto_pairs").currentData() == selected_id
        window._select_plant_orthophoto_pair("P1", foreign['pair_id'])
        assert window._plant_orthophoto_pair_id == selected_id
        stale_selector = overview(window).findChild(QComboBox, "plant_orthophoto_pairs")
        window._open_project("P2")
        stale_selector.setCurrentIndex(1 - stale_selector.currentIndex())
        assert window._plant_orthophoto_pair_id == foreign['pair_id']
        assert overview(window).findChild(QComboBox, "plant_orthophoto_pairs").count() == 1
        slider = overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider")
        slider.setValue(0)
        image = overview(window).findChild(QLabel, "orthophoto_comparison_image").pixmap().toImage()
        assert image.pixelColor(4, 4).getRgb() == (160, 160, 160, 255)
    finally:
        window.close()


@pytest.mark.parametrize("damage", ("missing_rgb", "missing_thermal", "corrupt", "no_overlap"))
def test_unavailable_registered_pair_fails_without_stale_image_and_can_be_retried(tmp_path, qapp, damage):
    window = offline_window(tmp_path / "projects.sqlite")
    service = window._project_service
    service.create_project("P1", "First")
    rgb, thermal = sources(tmp_path, "pair")
    service.register_project_orthophoto_pair("P1", rgb, thermal)
    before = service.state("P1")
    target = rgb if damage == "missing_rgb" else thermal
    original = target.read_bytes()
    try:
        window._open_project("P1")
        assert overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider") is not None
        if damage.startswith("missing"):
            target.unlink()
        elif damage == "corrupt":
            target.write_bytes(b"invalid synthetic TIFF")
        else:
            with rasterio.open(target, "r+") as dataset:
                dataset.transform = from_origin(400000., 5600000., .2, .2)
        overview(window).findChild(QPushButton, "refresh_plant_overview").click()
        assert overview(window).findChild(QLabel, "plant_orthophoto_error") is not None
        assert overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider") is None
        assert service.project_orthophoto_pairs("P1")
        target.write_bytes(original)
        overview(window).findChild(QPushButton, "refresh_plant_overview").click()
        assert overview(window).findChild(QLabel, "plant_orthophoto_error") is None
        assert overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider") is not None
        assert service.state("P1") == before
    finally:
        window.close()


def test_online_shell_never_loads_offline_pairs(tmp_path, qapp, monkeypatch):
    service = build_offline_services(tmp_path / "projects.sqlite").projects
    service.create_project("P1", "Offline only")
    def forbidden(*args):
        pytest.fail("online shell must not read local pairs or rasters")
    monkeypatch.setattr(service, "project_orthophoto_pairs", forbidden)
    window = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        # _refresh_import_page is an older independent boundary; exercise the
        # overview directly without entering another workflow's import path.
        window._current_project_id = "P1"
        window._refresh_plant_overview_page()
        window._select_plant_orthophoto_pair("P1", "arbitrary")
        assert overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider") is None
        assert overview(window).findChild(QLabel, "plant_orthophoto_empty_state") is not None
    finally:
        window.close()


@pytest.mark.parametrize("cancel", (False, True))
def test_processing_uses_existing_external_pair_intake_without_running_frozen_engine(
    tmp_path, qapp, monkeypatch, cancel,
):
    from pathlib import Path
    from mcm_solarcheck.domain.models import ThermalFrame
    from mcm_solarcheck.thermal.analysis import RawThermalStatistics
    from mcm_solarcheck.thermal.quality import ThermalQualityGrade, ThermalQualityResult

    database = tmp_path / "projects.sqlite"
    window = offline_window(database)
    service = window._project_service
    service.create_project("P1", "Synthetic originals imported")
    service.create_project("P2", "Other project")
    service.database.save_thermal_frame(
        "P1", ThermalFrame("T1", Path("synthetic.JPG"), 16, 12, thermal_source="raw"),
        ThermalQualityResult(ThermalQualityGrade.PASS, (), RawThermalStatistics(1, 10, 5., 5., 9., 10., 9)),
    )
    def forbidden_engine(*args, **kwargs):
        pytest.fail("GUI must not start the frozen native reconstruction")
    monkeypatch.setattr(service, "generate_imported_project_orthophotos", forbidden_engine)
    rgb, thermal = sources(tmp_path, "external")
    before = service.state("P1")
    try:
        window._open_project("P1")
        window._workflow_navigation.button(ShellRoute.PROCESSING).click()
        assert window.current_route is ShellRoute.PROCESSING
        processing = window._pages[ShellRoute.PROCESSING]
        assert "MicMac" in processing.findChild(
            QLabel, "processing_orthophoto_generation_status",
        ).text()
        old_button = processing.findChild(QPushButton, "processing_import_orthophoto_pair")
        assert old_button.isEnabled()
        old_button.click()
        assert window.current_route is ShellRoute.IMPORT
        page = window._pages[ShellRoute.IMPORT]
        assert page.findChild(QPushButton, "generate_orthophotos_button") is None
        paths = iter(("",) if cancel else (str(rgb), str(thermal)))
        monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([path] if (path := next(paths)) else [], ""))
        page.findChild(QPushButton, "register_orthophoto_pair_button").click()
        window._workflow_navigation.button(ShellRoute.PLANT_OVERVIEW).click()
        assert window.current_route is ShellRoute.PLANT_OVERVIEW
        assert len(service.project_orthophoto_pairs("P1")) == (0 if cancel else 1)
        assert (overview(window).findChild(QSlider, "orthophoto_thermal_opacity_slider") is None) == cancel
        assert service.state("P1") == before
        window._open_project("P2")
        window.show_route(ShellRoute.PROJECT)
        old_button.click()  # Stale processing-page callback from P1.
        assert window.current_route is ShellRoute.PROJECT
        assert service.project_orthophoto_pairs("P2") == ()
    finally:
        window.close()

    reopened = offline_window(database)
    try:
        reopened._open_project("P1")
        assert len(reopened._project_service.project_orthophoto_pairs("P1")) == (0 if cancel else 1)
        assert (overview(reopened).findChild(QSlider, "orthophoto_thermal_opacity_slider") is None) == cancel
    finally:
        reopened.close()


def test_online_shell_cannot_enter_local_orthophoto_intake(tmp_path, qapp):
    service = build_offline_services(tmp_path / "projects.sqlite").projects
    window = SolarCheckMainWindow(DeploymentMode.ONLINE, project_service=service)
    try:
        window._current_project_id = "P1"
        before = window.current_route
        window._open_orthophoto_pair_import("P1")
        assert window.current_route is before
        button = window._pages[ShellRoute.PROCESSING].findChild(QPushButton, "processing_import_orthophoto_pair")
        assert not button.isEnabled()
    finally:
        window.close()
