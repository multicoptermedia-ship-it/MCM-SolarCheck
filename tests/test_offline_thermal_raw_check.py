"""Synthetic tests for read-only per-frame DJI raw raster prerequisite.

These synthetic APP segments are not real DJI flight data or calibration.
"""
from __future__ import annotations

from hashlib import sha256

import pytest

from mcm_solarcheck.services.offline_thermal_raw_check import (
    ThermalRawCheckCancelled, check_imported_thermal_raw,
)
from mcm_solarcheck.services.workflow import WorkflowStage
from mcm_solarcheck.offline.composition import build_offline_services


def segment(marker, payload):
    return b"\xff" + bytes((marker,)) + (len(payload) + 2).to_bytes(2, "big") + payload


def synthetic_raw():
    raw = b"\x25\x01" * (640 * 512)
    app3 = b"".join(
        segment(0xE3, raw[i:i + 65532])
        for i in range(0, len(raw), 65532)
    )
    return b"fake-container" + app3 + segment(0xE4, bytes(256)) + segment(
        0xE5, bytes(23818)
    ) + b"fake-tail"


def seed(tmp_path, *, checksum=True, dimensions=(640, 512)):
    service = build_offline_services(tmp_path / "isolated.sqlite3").projects
    service.create_project("P1", "Synthetic thermal")
    service.create_project("P2", "Other project")
    image = tmp_path / "synthetic-m3t.JPG"
    image.write_bytes(synthetic_raw())
    with service.database.connect() as sql:
        sql.execute(
            "INSERT INTO thermal_frames "
            "(project_id,frame_id,source_file,thermal_source,width,height) "
            "VALUES (?,?,?,?,?,?)",
            ("P1", "T1", str(image), "DJI M3T APP3 raw", *dimensions),
        )
        if checksum:
            sql.execute(
                "INSERT INTO training_samples "
                "(sample_id,project_id,source_frame_id,source_file,modality,"
                "content_sha256,label_status,rights_status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("S1", "P1", "T1", str(image), "thermal",
                 sha256(image.read_bytes()).hexdigest(), "unlabeled", "unverified"),
            )
    return service, image


def test_valid_16bit_raster_matching_import_digest_is_only_readiness(tmp_path):
    service, source = seed(tmp_path)
    original = source.read_bytes()
    progress = []
    result = check_imported_thermal_raw(
        service.database, "P1",
        on_progress=lambda checked, total, issues: progress.append(
            (checked, total, issues)
        ),
    )
    assert result.total == result.checked == result.valid_rasters == 1
    assert result.checksum_verified == 1
    assert result.without_checksum == result.issues == 0
    assert not result.changed_inputs
    assert result.ready_for_later_analysis
    assert result.read_only
    assert progress == [(1, 1, 0)]
    assert source.read_bytes() == original
    assert not service.state("P1").readiness(WorkflowStage.REVIEW).ready
    assert not service.state("P1").readiness(WorkflowStage.REPORT).ready
    with service.database.connect() as sql:
        assert sql.execute("SELECT COUNT(*) FROM offline_processing_runs").fetchone()[0] == 0
        assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0
    other = check_imported_thermal_raw(service.database, "P2")
    assert other.total == other.valid_rasters == 0
    assert not other.ready_for_later_analysis


def test_no_import_hash_is_not_authenticated(tmp_path):
    service, _ = seed(tmp_path, checksum=False)
    result = check_imported_thermal_raw(service.database, "P1")
    assert result.valid_rasters == result.without_checksum == 1
    assert result.checksum_verified == result.issues == 0
    assert not result.ready_for_later_analysis


@pytest.mark.parametrize("mode", ("corrupt", "bad_hash", "wrong_dimensions", "missing"))
def test_invalid_files_and_provenance_fail_closed(tmp_path, mode):
    dimensions = (1, 1) if mode == "wrong_dimensions" else (640, 512)
    service, source = seed(tmp_path, dimensions=dimensions)
    if mode == "corrupt":
        source.write_bytes(b"\xff\xd8 not a radiometric stream")
    elif mode == "bad_hash":
        source.write_bytes(synthetic_raw() + b"alteration")
    elif mode == "missing":
        source.unlink()
    result = check_imported_thermal_raw(service.database, "P1")
    assert result.valid_rasters == 0
    assert result.issues == 1
    assert not result.ready_for_later_analysis
    assert not service.state("P1").readiness(WorkflowStage.REVIEW).ready


def test_cancel_and_size_limits_do_not_return_approved_result(tmp_path):
    service, source = seed(tmp_path)
    with pytest.raises(ThermalRawCheckCancelled):
        check_imported_thermal_raw(
            service.database, "P1", should_cancel=lambda: True,
        )
    cancelled = {"value": False}
    with pytest.raises(ThermalRawCheckCancelled):
        check_imported_thermal_raw(
            service.database, "P1",
            should_cancel=lambda: cancelled["value"],
            on_progress=lambda *_: cancelled.__setitem__("value", True),
        )
    too_small = check_imported_thermal_raw(
        service.database, "P1", maximum_bytes=1024,
    )
    assert too_small.issues == 1
    assert not too_small.ready_for_later_analysis
    assert source.is_file()
    with pytest.raises(ValueError, match="byte bound"):
        check_imported_thermal_raw(service.database, "P1", maximum_bytes=0)


def test_change_to_other_project_does_not_create_cross_project_result(tmp_path):
    service, source = seed(tmp_path)
    def change_input(checked, total, issues):
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames(project_id,frame_id,source_file) "
                "VALUES (?,?,?)", ("P1", "RGB", str(source)),
            )
    result = check_imported_thermal_raw(
        service.database, "P1", on_progress=change_input,
    )
    assert result.changed_inputs
    assert not result.ready_for_later_analysis
    assert check_imported_thermal_raw(service.database, "P2").total == 0
