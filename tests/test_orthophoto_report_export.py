import numpy as np
import rasterio
from rasterio.enums import ColorInterp
from rasterio.transform import from_origin
from mcm_solarcheck.services.orthophoto_report_export import export_pilot_pdf_with_rgb_orthophoto
from mcm_solarcheck.services.pv_pilot_report_sample import fictional_pilot_report


def test_orthophoto_pdf_pipeline(tmp_path):
    source = tmp_path / 'rgb.tif'
    with rasterio.open(source, 'w', driver='GTiff', width=8, height=8, count=3, dtype='uint8', crs='EPSG:25832', transform=from_origin(500000, 5600000, 0.1, 0.1)) as dataset:
        for band in range(1, 4):
            dataset.write(np.full((8, 8), band * 20, dtype=np.uint8), band)
        dataset.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)
    target = tmp_path / 'report.pdf'
    assert export_pilot_pdf_with_rgb_orthophoto(fictional_pilot_report(), source, target) == target
    assert target.read_bytes().startswith(b'%PDF')
    assert sorted(p.name for p in tmp_path.iterdir()) == ['report.pdf', 'rgb.tif']


def test_reject_invalid_report_and_existing_pdf(tmp_path):
    import pytest
    source = tmp_path / 'missing.tif'
    target = tmp_path / 'report.pdf'
    with pytest.raises(TypeError, match='PilotReport'):
        export_pilot_pdf_with_rgb_orthophoto(object(), source, target)
    target.write_bytes(b'keep')
    with pytest.raises(FileExistsError):
        export_pilot_pdf_with_rgb_orthophoto(fictional_pilot_report(), source, target)
    assert target.read_bytes() == b'keep'
