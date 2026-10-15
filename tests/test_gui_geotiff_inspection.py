"""Read-only GeoTIFF desktop integration tests."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import pytest
from PySide6.QtWidgets import QApplication

@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])

from mcm_solarcheck.gui.import_page import make_import_page
from mcm_solarcheck.services.orthomosaic_geotiff_contract import GeoTIFFSpatialReference


def test_import_page_geotiff_picker_requires_project_and_callback(qapp):
    page = make_import_page()
    assert not page.findChild(__import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton, "inspect_geotiff_button").isEnabled()


def test_import_page_geotiff_picker_calls_selected_file(qapp):
    from PySide6.QtWidgets import QPushButton
    paths = []
    page = make_import_page(
        current_project_id="P1",
        on_inspect_geotiff=paths.append,
        choose_geotiff=lambda: "/tmp/orthophoto.tif",
        geotiff_result="GIS-Metadaten vorhanden (nicht fachlich verifiziert)",
    )
    button = page.findChild(QPushButton, "inspect_geotiff_button")
    assert button.isEnabled()
    button.click()
    assert paths == ["/tmp/orthophoto.tif"]


def test_project_service_rejects_unknown_project_before_inspection():
    from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
    service = object.__new__(ProjectApplicationService)
    service.projects = lambda: ()
    try:
        service.inspect_project_geotiff("missing", "image.tif")
    except KeyError as error:
        assert "Unknown project" in str(error)
    else:
        raise AssertionError("Unknown project must be rejected")


def test_real_offline_project_geotiff_inspection_through_desktop(tmp_path, qapp):
    import numpy as np
    from PySide6.QtWidgets import QLabel
    from mcm_solarcheck.offline.composition import build_offline_services
    from mcm_solarcheck.gui.shell import SolarCheckMainWindow
    from mcm_solarcheck.services.deployment import DeploymentMode
    from mcm_solarcheck.services.shell_navigation import ShellRoute
    from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
        GeoTIFFSpatialReference, write_georeferenced_rgb_geotiff,
    )

    service = build_offline_services(tmp_path / "inspection.sqlite").projects
    service.create_project("GIS-01", "Lokales GIS-Projekt")
    ref = GeoTIFFSpatialReference(
        "EPSG:25832", (0.1, 0, 350000, 0, -0.1, 5650000), 2, 3
    )
    tif = write_georeferenced_rgb_geotiff(
        np.zeros((3, 2, 3), dtype=np.uint8),
        tmp_path / "webodm-result.tif", ref, georeferencing_verified=True,
    )
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    window._open_project("GIS-01")
    before = service.state("GIS-01")
    window._inspect_project_geotiff(str(tif))
    label = window._pages[ShellRoute.IMPORT].findChild(QLabel, "geotiff_inspection_result")
    assert label is not None
    assert "EPSG:25832" in label.text()
    assert "nicht fachlich verifiziert" in label.text()
    assert service.state("GIS-01") == before


def test_desktop_geotiff_failure_does_not_change_project_workflow(tmp_path, qapp):
    from PySide6.QtWidgets import QLabel
    from mcm_solarcheck.offline.composition import build_offline_services
    from mcm_solarcheck.gui.shell import SolarCheckMainWindow
    from mcm_solarcheck.services.deployment import DeploymentMode
    from mcm_solarcheck.services.shell_navigation import ShellRoute

    service = build_offline_services(tmp_path / "failure.sqlite").projects
    service.create_project("GIS-ERR", "GIS Fehlerfall")
    broken = tmp_path / "broken.tif"
    broken.write_bytes(b"invalid")
    window = SolarCheckMainWindow(DeploymentMode.OFFLINE_DESKTOP, project_service=service)
    window._open_project("GIS-ERR")
    before = service.state("GIS-ERR")
    window._inspect_project_geotiff(str(broken))
    label = window._pages[ShellRoute.IMPORT].findChild(QLabel, "geotiff_inspection_result")
    assert label is not None
    assert "fehlgeschlagen" in label.text()
    assert service.state("GIS-ERR") == before
