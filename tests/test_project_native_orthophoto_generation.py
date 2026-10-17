"""Project-bound native orthophoto generation rejects unverified geometry."""
import pytest
from mcm_solarcheck.services.project_pipeline import ProjectApplicationService
from mcm_solarcheck.storage.sqlite import ProjectDatabase
from mcm_solarcheck.services.orthomosaic_geotiff_contract import GeoTIFFSpatialReference


def test_project_native_orthophoto_requires_existing_project_and_survey(tmp_path):
    database = ProjectDatabase(tmp_path / "projects.sqlite")
    database.initialize()
    service = ProjectApplicationService(database)
    reference = GeoTIFFSpatialReference("EPSG:25832", (1., 0., 0., 0., 1., 0.), 8, 8)
    arguments = ((), (), (), (), reference, reference, tmp_path / "rgb.tif", tmp_path / "thermal.tif")
    with pytest.raises(KeyError, match="Unknown project"):
        service.generate_project_planar_orthophotos("missing", *arguments)
    service.create_project("p1", "PV")
    with pytest.raises(ValueError, match="surface"):
        service.generate_project_planar_orthophotos("p1", *arguments)
    assert not (tmp_path / "rgb.tif").exists()
    assert not (tmp_path / "thermal.tif").exists()
