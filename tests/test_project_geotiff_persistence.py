"""Project-scoped, unapproved GeoTIFF provenance persistence."""
import hashlib

import numpy as np
import pytest

from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services.orthomosaic_geotiff_contract import (
    GeoTIFFSpatialReference, write_georeferenced_rgb_geotiff,
)


def test_register_project_geotiff_persists_provenance_without_workflow_change(tmp_path):
    database = tmp_path / "projects.sqlite"
    service = build_offline_services(database).projects
    service.create_project("P1", "First")
    service.create_project("P2", "Second")
    ref = GeoTIFFSpatialReference(
        "EPSG:25832", (0.1, 0, 350000, 0, -0.1, 5650000), 2, 3
    )
    source = write_georeferenced_rgb_geotiff(
        np.zeros((3, 2, 3), dtype=np.uint8),
        tmp_path / "webodm.tif", ref, georeferencing_verified=True,
    )
    before = service.state("P1")
    service.register_project_geotiff("P1", source, source_kind="webodm")
    rows = build_offline_services(database).projects.project_geotiff_inspections("P1")
    assert len(rows) == 1
    assert rows[0]["source_path"] == str(source.resolve())
    assert rows[0]["source_kind"] == "webodm"
    assert rows[0]["content_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert rows[0]["inspection_status"] == "metadata_only"
    assert rows[0]["crs"] == "EPSG:25832"
    assert service.project_geotiff_inspections("P2") == ()
    assert service.state("P1") == before


def test_registration_rejects_unknown_provenance_before_database_write(tmp_path):
    service = build_offline_services(tmp_path / "projects.sqlite").projects
    service.create_project("P1", "First")
    with pytest.raises(ValueError, match="source_kind"):
        service.register_project_geotiff("P1", tmp_path / "absent.tif", source_kind="untrusted")
    assert service.project_geotiff_inspections("P1") == ()
