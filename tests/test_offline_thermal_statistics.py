"""Regression for offline read-only sensor-space statistics only.

Synthetic APP3 data; no real customer assets and no radiometric calibration.
"""
from __future__ import annotations

from hashlib import sha256

import pytest

from mcm_solarcheck.offline.composition import build_offline_services
from mcm_solarcheck.services.offline_thermal_raw_check import ThermalRawCheckCancelled
from mcm_solarcheck.services.offline_thermal_statistics import (
    analyze_imported_thermal_sensor_values,
)
from mcm_solarcheck.services.workflow import WorkflowStage


def segment(marker, data):
    return b"\xff" + bytes([marker]) + (len(data) + 2).to_bytes(2, "big") + data


def raster_bytes(*, varied=True):
    raw = (b"\x01\x00" + b"\x02\x00") * (640 * 512 // 2) if varied else (
        b"\x2a\x00" * (640 * 512)
    )
    return (
        b"synthetic-not-dji-jpg"
        + b"".join(segment(0xE3, raw[i:i + 65532]) for i in range(0, len(raw), 65532))
        + segment(0xE4, bytes(256))
        + segment(0xE5, bytes(23818))
    )


def seed(tmp_path, *, varied=True, expected_digest=True):
    service = build_offline_services(tmp_path / "statistics.sqlite").projects
    service.create_project("P1", "Synthetic project")
    service.create_project("P2", "Other project")
    image = tmp_path / "synthetic.JPG"
    image.write_bytes(raster_bytes(varied=varied))
    with service.database.connect() as sql:
        sql.execute(
            "INSERT INTO thermal_frames "
            "(project_id,frame_id,source_file,thermal_source,width,height) "
            "VALUES (?,?,?,?,?,?)",
            ("P1", "T1", str(image), "raw", 640, 512),
        )
        if expected_digest:
            sql.execute(
                "INSERT INTO training_samples "
                "(sample_id,project_id,source_frame_id,source_file,modality,"
                "content_sha256,label_status,rights_status) "
                "VALUES (?,?,?,?,?,?,?,?)",
                ("s1", "P1", "T1", str(image), "thermal",
                 sha256(image.read_bytes()).hexdigest(),
                 "pending", "private"),
            )
    return service, image


def test_verified_thermal_statistics_are_real_but_never_processing_completion(tmp_path):
    service, image = seed(tmp_path)
    initial = image.read_bytes()
    seen = []
    result = analyze_imported_thermal_sensor_values(
        service.database, "P1",
        on_progress=lambda *args: seen.append(args),
    )
    assert result.total == result.checked == result.analyzed == 1
    assert result.issues == result.without_checksum == 0
    assert result.minimum_raw_value == 1
    assert result.maximum_raw_value == 2
    assert result.varying_frames == 1
    assert result.constant_frames == 0
    assert result.valid_for_raw_statistics_only
    assert result.read_only
    assert seen == [(1, 1, 0)]
    assert image.read_bytes() == initial
    assert not service.state("P1").readiness(WorkflowStage.REVIEW).ready
    assert not service.state("P1").readiness(WorkflowStage.REPORT).ready
    assert not service.state("P1").readiness(WorkflowStage.EXPORT).ready
    assert analyze_imported_thermal_sensor_values(service.database, "P2").total == 0
    with service.database.connect() as sql:
        assert sql.execute("SELECT COUNT(*) FROM offline_processing_runs").fetchone()[0] == 0
        assert sql.execute("SELECT COUNT(*) FROM finding_reviews").fetchone()[0] == 0


def test_constant_raw_sensor_image_is_not_called_a_hotspot(tmp_path):
    service, _ = seed(tmp_path, varied=False)
    result = analyze_imported_thermal_sensor_values(service.database, "P1")
    assert result.analyzed == 1
    assert result.constant_frames == 1
    assert result.varying_frames == 0
    assert result.minimum_raw_value == result.maximum_raw_value == 42
    assert result.valid_for_raw_statistics_only
    assert not service.state("P1").readiness(WorkflowStage.REVIEW).ready


@pytest.mark.parametrize("mode", ["absent_digest", "corrupt", "changed_bytes", "missing", "size_limit"])
def test_untrusted_or_invalid_inputs_never_produce_statistics(tmp_path, mode):
    service, image = seed(tmp_path, expected_digest=mode!="absent_digest")
    if mode == "corrupt":
        image.write_bytes(b"invalid")
    if mode == "changed_bytes":
        image.write_bytes(image.read_bytes() + b"mutation")
    if mode == "missing":
        image.unlink()
    args = {"maximum_bytes": 10} if mode == "size_limit" else {}
    result = analyze_imported_thermal_sensor_values(service.database, "P1", **args)
    assert result.analyzed == 0
    assert result.minimum_raw_value is None
    assert result.maximum_raw_value is None
    assert not result.valid_for_raw_statistics_only
    if mode == "absent_digest":
        assert result.without_checksum == 1 and result.issues == 0
    else:
        assert result.issues == 1 and result.without_checksum == 0


def test_cancellation_and_input_fingerprint_changes_are_fail_closed(tmp_path):
    service, image = seed(tmp_path)
    with pytest.raises(ThermalRawCheckCancelled):
        analyze_imported_thermal_sensor_values(
            service.database, "P1", should_cancel=lambda: True,
        )
    stop = {"now": False}
    with pytest.raises(ThermalRawCheckCancelled):
        analyze_imported_thermal_sensor_values(
            service.database, "P1",
            should_cancel=lambda: stop["now"],
            on_progress=lambda *_: stop.__setitem__("now", True),
        )
    def change_input(*_):
        with service.database.connect() as sql:
            sql.execute(
                "INSERT INTO image_frames(project_id,frame_id,source_file)"
                " VALUES (?,?,?)", ("P1", "R1", str(image)),
            )
    stale = analyze_imported_thermal_sensor_values(
        service.database, "P1", on_progress=change_input,
    )
    assert stale.changed_inputs
    assert not stale.valid_for_raw_statistics_only
    with pytest.raises(ValueError, match="byte bound"):
        analyze_imported_thermal_sensor_values(
            service.database, "P1", maximum_bytes=0,
        )
