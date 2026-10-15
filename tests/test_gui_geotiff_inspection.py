"""Read-only GeoTIFF desktop integration tests."""
from types import SimpleNamespace

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
