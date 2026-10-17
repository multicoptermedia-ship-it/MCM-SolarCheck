"""Report overview must never masquerade as orthophoto or recorded flight path."""
import numpy as np
import pytest
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin

from mcm_solarcheck.services.orthophoto_report_overview import create_rgb_orthophoto_report_preview


def make_rgb(path, *, count=3):
    with rasterio.open(path, "w", driver="GTiff", width=8, height=4, count=count,
                       dtype="uint8", crs="EPSG:32632", transform=from_origin(500000, 5600000, 0.1, 0.1)) as ds:
        for band in range(1, count + 1):
            ds.write(np.full((4, 8), band * 20, dtype=np.uint8), band)
        if count == 3:
            ds.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)


def test_rgb_geotiff_preview_for_report_is_bounded_and_not_flight_proof(tmp_path):
    source = tmp_path / "rgb.tif"
    make_rgb(source)
    result = create_rgb_orthophoto_report_preview(source, tmp_path / "overview.png", max_side=4)
    assert result.image_path.is_file()
    assert result.path_kind == "not_available"
    assert "kein Flugpfadnachweis" in result.source_note
    from PIL import Image
    with Image.open(result.image_path) as image:
        assert image.size == (4, 2)
        assert image.getpixel((0, 0)) == (20, 40, 60)


def test_reject_non_rgb_geotiff_and_existing_target(tmp_path):
    thermal = tmp_path / "thermal.tif"
    make_rgb(thermal, count=1)
    with pytest.raises(ValueError, match="three-band"):
        create_rgb_orthophoto_report_preview(thermal, tmp_path / "thermal.png")
    source = tmp_path / "rgb.tif"
    make_rgb(source)
    target = tmp_path / "existing.png"
    target.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        create_rgb_orthophoto_report_preview(source, target)
    assert target.read_bytes() == b"keep"


def test_pdf_report_embeds_rgb_orthophoto_without_claiming_recorded_path(tmp_path):
    from mcm_solarcheck.services.pv_pilot_pdf_export import export_pilot_pdf
    from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report
    from mcm_solarcheck.services.pv_pilot_flight_overview import flight_overview_label

    source = tmp_path / "rgb.tif"
    make_rgb(source)
    overview = create_rgb_orthophoto_report_preview(source, tmp_path / "overview.png")
    assert "kein verifizierter Flugpfad" in flight_overview_label(overview)
    pdf = export_pilot_pdf(fictional_pilot_report(), tmp_path / "report.pdf",
                           flight_overview=overview)
    assert pdf.read_bytes().startswith(b"%PDF")
    assert pdf.stat().st_size > 1000
