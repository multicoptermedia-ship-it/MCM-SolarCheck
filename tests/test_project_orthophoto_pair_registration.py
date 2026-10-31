"""Existing local RGB/thermal GIS files register atomically, without approval."""
import hashlib
import math
import sqlite3

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.storage.sqlite import ProjectDatabase


def _raster(path, values, *, origin_x=300000., pixel_size=1., nodata=None):
    values = np.asarray(values)
    if values.ndim == 2:
        values = values[None]
    with rasterio.open(
        path, "w", driver="GTiff", count=len(values),
        width=values.shape[2], height=values.shape[1], dtype=values.dtype,
        crs="EPSG:25832", transform=from_origin(origin_x, 5600000., pixel_size, pixel_size),
        nodata=nodata,
    ) as dataset:
        dataset.write(values)
    return path


def _scene(tmp_path, *, thermal_rgb=False, thermal_nodata=None, empty_rgb=False):
    service = build_offline_services(tmp_path / "projects.sqlite").projects
    service.create_project("P1", "First")
    service.create_project("P2", "Second")
    rgb_values = np.full((3, 4, 4), 40, np.uint8)
    if empty_rgb:
        rgb_values[:] = 0
    rgb = _raster(tmp_path / "rgb.tif", rgb_values, nodata=0 if empty_rgb else None)
    if thermal_rgb:
        thermal_values = np.stack([np.full((2, 2), v, np.uint8) for v in (12, 100, 200)])
    else:
        thermal_values = np.asarray([[18., 19.], [20., 21.]], np.float32)
        if thermal_nodata is not None and math.isnan(thermal_nodata):
            thermal_values[0, 0] = np.nan
    thermal = _raster(tmp_path / "thermal.tif", thermal_values,
                      pixel_size=2., nodata=thermal_nodata)
    return service, rgb, thermal


def test_pair_registration_is_persistent_project_scoped_idempotent_and_read_only(tmp_path):
    service, rgb, thermal = _scene(tmp_path)
    original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)}
    before = service.state("P1")
    pair = service.register_project_orthophoto_pair(
        "P1", rgb, thermal, source_kind="micmac", thermal_value_kind="sensor_values",
    )
    assert pair["rgb_source_path"] == str(rgb.resolve())
    assert pair["thermal_source_path"] == str(thermal.resolve())
    assert pair["source_kind"] == "micmac"
    assert pair["thermal_value_kind"] == "sensor_values"
    assert pair["inspection_status"] == "metadata_only"
    assert pair["common_pixel_fraction"] == pytest.approx(1.)
    assert not any("temperature" in key or "verified" in key for key in pair)
    reopened = build_offline_services(service.database.path).projects
    assert reopened.project_orthophoto_pairs("P1") == (pair,)
    assert reopened.project_orthophoto_pairs("P2") == ()
    assert reopened.register_project_orthophoto_pair(
        "P1", rgb, thermal, source_kind="micmac", thermal_value_kind="sensor_values",
    ) == pair
    assert len(reopened.project_geotiff_inspections("P1")) == 2
    assert reopened.state("P1") == before
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (rgb, thermal)} == original


def test_previously_registered_rgb_is_reused_without_overwriting_provenance(tmp_path):
    service, rgb, thermal = _scene(tmp_path)
    service.register_project_geotiff("P1", rgb, source_kind="unknown")
    pair = service.register_project_orthophoto_pair("P1", rgb, thermal, source_kind="micmac")
    rows = service.project_geotiff_inspections("P1")
    assert len(rows) == 2
    assert next(row for row in rows if row["source_path"] == str(rgb))["source_kind"] == "unknown"
    assert pair["source_kind"] == "micmac"


def test_invalid_second_raster_and_unknown_project_never_register_first(tmp_path):
    service, rgb, _thermal = _scene(tmp_path)
    bad = tmp_path / "invalid.tif"
    bad.write_bytes(b"not a GIS raster")
    with pytest.raises(ValueError):
        service.register_project_orthophoto_pair("P1", rgb, bad)
    assert service.project_geotiff_inspections("P1") == ()
    assert service.project_orthophoto_pairs("P1") == ()
    with pytest.raises(KeyError, match="Unknown project"):
        service.register_project_orthophoto_pair("absent", tmp_path / "missing.tif", bad)
    with pytest.raises(KeyError):
        service.project_orthophoto_pairs("absent")
    with pytest.raises(ValueError, match="GeoTIFF"):
        service.register_project_geotiff("P1", tmp_path / "missing.tif", source_kind="external_gis")
    assert service.project_geotiff_inspections("P1") == ()


def test_database_failure_on_second_inspection_rolls_back_entire_pair(tmp_path):
    service, rgb, thermal = _scene(tmp_path)
    before = service.state("P1")
    with service.database.connect() as connection:
        connection.execute("""CREATE TRIGGER reject_second_raster
            BEFORE INSERT ON project_geotiffs
            WHEN NEW.source_path LIKE '%thermal.tif'
            BEGIN SELECT RAISE(ABORT, 'synthetic second insert failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="second insert failure"):
        service.register_project_orthophoto_pair("P1", rgb, thermal)
    assert service.project_geotiff_inspections("P1") == ()
    assert service.project_orthophoto_pairs("P1") == ()
    assert service.state("P1") == before


def test_pair_insert_failure_also_rolls_back_both_source_inspections(tmp_path):
    service, rgb, thermal = _scene(tmp_path)
    with service.database.connect() as connection:
        connection.execute("""CREATE TRIGGER reject_pair BEFORE INSERT ON project_orthophoto_pairs
            BEGIN SELECT RAISE(ABORT, 'synthetic pair insert failure'); END""")
    with pytest.raises(sqlite3.IntegrityError, match="pair insert failure"):
        service.register_project_orthophoto_pair("P1", rgb, thermal)
    assert service.project_geotiff_inspections("P1") == ()
    assert service.project_orthophoto_pairs("P1") == ()


def test_existing_provenance_must_still_describe_the_actual_source(tmp_path):
    service, rgb, thermal = _scene(tmp_path)
    service.register_project_geotiff("P1", rgb, source_kind="external_gis")
    with service.database.connect() as connection:
        connection.execute("UPDATE project_geotiffs SET width=999 WHERE project_id='P1'")
    with pytest.raises(ValueError, match="metadata differs"):
        service.register_project_orthophoto_pair("P1", rgb, thermal)
    assert len(service.project_geotiff_inspections("P1")) == 1
    assert service.project_orthophoto_pairs("P1") == ()


def test_nan_nodata_survives_sqlite_as_explicit_pair_semantics(tmp_path):
    service, rgb, thermal = _scene(tmp_path, thermal_nodata=np.nan)
    pair = service.register_project_orthophoto_pair(
        "P1", rgb, thermal, thermal_value_kind="sensor_values",
    )
    assert pair["thermal_nodata_kind"] == "nan"
    assert pair["common_pixel_fraction"] == pytest.approx(.75)
    reopened = build_offline_services(service.database.path).projects
    assert reopened.project_orthophoto_pairs("P1")[0]["thermal_nodata_kind"] == "nan"
    with rasterio.open(thermal) as dataset:
        assert math.isnan(dataset.nodata)


def test_visual_thermal_is_not_accepted_as_sensor_values_or_celsius(tmp_path):
    service, rgb, thermal = _scene(tmp_path, thermal_rgb=True)
    with pytest.raises(ValueError, match="one numeric band"):
        service.register_project_orthophoto_pair("P1", rgb, thermal, thermal_value_kind="sensor_values")
    with pytest.raises(ValueError, match="Celsius"):
        service.register_project_orthophoto_pair("P1", rgb, thermal, thermal_value_kind="celsius")
    assert service.project_geotiff_inspections("P1") == ()
    pair = service.register_project_orthophoto_pair("P1", rgb, thermal)
    assert pair["thermal_value_kind"] == "visual"


def test_empty_rgb_and_nonoverlapping_geotiffs_cannot_form_pair(tmp_path):
    service, rgb, thermal = _scene(tmp_path, empty_rgb=True)
    with pytest.raises(ValueError, match="overlapping valid pixels"):
        service.register_project_orthophoto_pair("P1", rgb, thermal)
    assert service.project_geotiff_inspections("P1") == ()
    _raster(rgb, np.full((3, 4, 4), 40, np.uint8), origin_x=310000.)
    with pytest.raises(ValueError, match="overlapping valid pixels"):
        service.register_project_orthophoto_pair("P1", rgb, thermal)
    assert service.project_orthophoto_pairs("P1") == ()


def test_pair_cannot_reinterpret_existing_files_or_reuse_changed_inspection(tmp_path):
    service, rgb, thermal = _scene(tmp_path)
    first = service.register_project_orthophoto_pair("P1", rgb, thermal)
    with pytest.raises(ValueError, match="different source semantics"):
        service.register_project_orthophoto_pair("P1", rgb, thermal, thermal_value_kind="sensor_values")
    assert service.project_orthophoto_pairs("P1") == (first,)
    _raster(thermal, np.full((2, 2), 35., np.float32), pixel_size=2.)
    with pytest.raises(ValueError, match="source changed"):
        service.register_project_orthophoto_pair("P1", rgb, thermal)
    assert service.project_orthophoto_pairs("P1") == (first,)


def test_same_file_and_symlink_sources_are_rejected(tmp_path):
    service, rgb, thermal = _scene(tmp_path)
    with pytest.raises(ValueError, match="distinct files"):
        service.register_project_orthophoto_pair("P1", rgb, rgb)
    link = tmp_path / "linked.tif"
    try:
        link.symlink_to(thermal)
    except OSError:
        pytest.skip("Symlink creation unavailable on this platform")
    with pytest.raises(ValueError, match="symlink"):
        service.register_project_orthophoto_pair("P1", rgb, link)
    assert service.project_geotiff_inspections("P1") == ()


def test_v21_migration_adds_pair_table_and_keeps_existing_gis_provenance(tmp_path):
    service, rgb, _thermal = _scene(tmp_path)
    service.register_project_geotiff("P1", rgb, source_kind="external_gis")
    before = service.project_geotiff_inspections("P1")
    with service.database.connect() as connection:
        connection.execute("DROP TABLE project_orthophoto_pairs")
        connection.execute("UPDATE schema_info SET version=21")
    migrated = ProjectDatabase(service.database.path)
    migrated.initialize()
    assert migrated.geotiff_inspections("P1") == before
    assert migrated.orthophoto_pairs("P1") == ()
    with migrated.connect() as connection:
        assert connection.execute("SELECT version FROM schema_info").fetchone()[0] == 22
        fields = {row["name"] for row in connection.execute("PRAGMA table_info(project_orthophoto_pairs)")}
        assert {"rgb_source_path", "thermal_source_path", "thermal_value_kind", "thermal_nodata_kind"} <= fields
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
