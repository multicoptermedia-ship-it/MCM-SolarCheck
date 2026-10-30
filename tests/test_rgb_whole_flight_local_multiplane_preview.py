"""Private opt-in whole-flight -> actual multi-facet RGBA PNG handoff (synthetic)."""
import json
from dataclasses import replace

import cv2
import numpy as np
import pytest

from mcm_solarcheck.services import rgb_zip_whole_flight_cli as cli
from mcm_solarcheck.services.rgb_private_multi_plane_preview import (
    PrivateRGBMultiPlaneOrthopreview,
)
from mcm_solarcheck.services.rgb_zip_whole_flight_reconstruction import (
    PrivateRGBFlightStageError,
)


class _SuccessfulSyntheticFlight:
    rtk_windowed_ba = object()

    def privacy_safe_summary(self):
        return {
            "schema": "mcm.private_complete_rgb_flight_reconstruction.v1",
            "status": "whole_rgb_rtk_windowed_ba_candidate_not_an_orthophoto",
            "frame_count": 160,
            "rgb_orthophoto_verified": False,
            "roof_geometry_verified": False,
        }


def _private_preview():
    rgb = np.array(
        [[[250, 25, 10], [100, 150, 200]],
         [[90, 180, 40], [123, 234, 111]]], dtype=np.uint8,
    )
    mask = np.array([[True, False], [True, True]], dtype=bool)
    return PrivateRGBMultiPlaneOrthopreview(
        rgb, mask, ~mask, np.array([[0, -1], [1, 1]], dtype=np.int16),
        (315.123, 987.456), .05, 2, (2, 3), 1, 3,
    )


def _paths(tmp_path):
    source_dir = tmp_path / "immutable-originals"
    source_dir.mkdir()
    archive = source_dir / "RGB2.tip"
    archive.write_bytes(b"private source original remains unchanged")
    calibration = tmp_path / "external-lens.json"
    calibration.write_text("{}", encoding="utf-8")
    destination_dir = tmp_path / "private-output"
    destination_dir.mkdir()
    return archive, calibration, destination_dir


def test_opt_in_writes_rgba_only_to_separate_private_directory(
    tmp_path, monkeypatch, capsys,
):
    archive, calibration, output_dir = _paths(tmp_path)
    before = archive.read_bytes()
    preview = _private_preview()
    seen = []
    monkeypatch.setattr(
        cli, "reconstruct_private_complete_rgb_zip_flight",
        lambda archives, calibration, **kw: _SuccessfulSyntheticFlight(),
    )

    def render(archives, calibration, ba, **kw):
        seen.append((archives, kw))
        assert ba is _SuccessfulSyntheticFlight.rtk_windowed_ba
        assert kw["meters_per_pixel"] == .05
        return preview

    monkeypatch.setattr(
        cli, "render_private_multiplane_preview_from_original_rgb_archives", render,
    )
    outfile = output_dir / "private-3d-preview.png"
    report = output_dir / "quality.json"
    status = cli.main([
        "--rgb-archive", str(archive),
        "--calibration-json", str(calibration),
        "--report", str(report),
        "--private-preview-png", str(outfile),
    ])
    assert status == 0
    assert len(seen) == 1 and archive.read_bytes() == before
    image = cv2.imdecode(np.frombuffer(outfile.read_bytes(), np.uint8),
                        cv2.IMREAD_UNCHANGED)
    assert image.shape == (2, 2, 4)
    np.testing.assert_array_equal(image[0, 0], [10, 25, 250, 255])
    np.testing.assert_array_equal(image[0, 1], [0, 0, 0, 0])
    assert image[1, 0, 3] == 255
    private_report = json.loads(report.read_text(encoding="utf-8"))
    assert private_report["private_preview_png_written"] is True
    assert private_report["private_multiplane_preview"]["orthophoto_verified"] is False
    stdout = capsys.readouterr().out
    assert json.loads(stdout) == private_report
    for secret in ("315.123", "987.456", "RGB2.tip", "private-output", "250, 25, 10"):
        assert secret not in stdout and secret not in report.read_text()


def test_failed_render_returns_failure_and_never_writes_misleading_png(
    tmp_path, monkeypatch, capsys,
):
    archive, calibration, output_dir = _paths(tmp_path)
    monkeypatch.setattr(
        cli, "reconstruct_private_complete_rgb_zip_flight",
        lambda *a, **kw: _SuccessfulSyntheticFlight(),
    )
    monkeypatch.setattr(
        cli, "render_private_multiplane_preview_from_original_rgb_archives",
        lambda *a, **kw: replace(
            _private_preview(), valid_mask_private=np.zeros((2, 2), dtype=bool),
            valid_pixel_count=0,
        ),
    )
    outfile = output_dir / "must-not-exist.png"
    report = output_dir / "failure.json"
    status = cli.main([
        "--rgb-archive", str(archive),
        "--calibration-json", str(calibration),
        "--report", str(report),
        "--private-preview-png", str(outfile),
    ])
    assert status == 2 and not outfile.exists()
    summary = json.loads(capsys.readouterr().out)
    assert summary["failed_stage"] == "multiplane_preview"
    assert summary["private_preview_png_written"] is False
    assert summary["rgb_orthophoto_verified"] is False
    assert summary == json.loads(report.read_text())


def test_strict_geometry_failure_never_renders_a_private_png(
    tmp_path, monkeypatch,
):
    archive, calibration, output_dir = _paths(tmp_path)

    def fail(*a, **kw):
        raise PrivateRGBFlightStageError("global_sfm")

    monkeypatch.setattr(cli, "reconstruct_private_complete_rgb_zip_flight", fail)
    monkeypatch.setattr(
        cli, "render_private_multiplane_preview_from_original_rgb_archives",
        lambda *a, **kw: pytest.fail("render must never run before valid BA"),
    )
    outfile = output_dir / "must-not-exist.png"
    report = output_dir / "failure.json"
    status = cli.main([
        "--rgb-archive", str(archive),
        "--calibration-json", str(calibration),
        "--report", str(report),
        "--private-preview-png", str(outfile),
    ])
    assert status == 2 and not outfile.exists()
    assert json.loads(report.read_text())["failed_stage"] == "global_sfm"


def test_preview_needs_a_report_and_a_private_non_checkout_new_path(
    tmp_path, monkeypatch,
):
    archive, calibration, output_dir = _paths(tmp_path)
    monkeypatch.setattr(
        cli, "reconstruct_private_complete_rgb_zip_flight",
        lambda *a, **kw: pytest.fail("invalid path must fail before SfM"),
    )
    root = ["--rgb-archive", str(archive), "--calibration-json", str(calibration)]
    with pytest.raises(ValueError, match="--report required"):
        cli.main(root + ["--private-preview-png", str(output_dir / "new.png")])
    report = output_dir / "quality.json"
    with pytest.raises(ValueError, match="outside checkout"):
        cli.main(root + ["--report", str(report),
                         "--private-preview-png", str(archive.parent / "unsafe.png")])
    existing = output_dir / "already.png"
    existing.write_bytes(b"do not overwrite")
    with pytest.raises(ValueError, match="new private PNG"):
        cli.main(root + ["--report", str(report),
                         "--private-preview-png", str(existing)])
    assert existing.read_bytes() == b"do not overwrite"


def test_opt_out_remains_aggregate_only(tmp_path, monkeypatch, capsys):
    archive, calibration, _ = _paths(tmp_path)
    monkeypatch.setattr(
        cli, "reconstruct_private_complete_rgb_zip_flight",
        lambda *a, **kw: _SuccessfulSyntheticFlight(),
    )
    monkeypatch.setattr(
        cli, "render_private_multiplane_preview_from_original_rgb_archives",
        lambda *a, **kw: pytest.fail("preview is opt-in only"),
    )
    assert cli.main(["--rgb-archive", str(archive),
                     "--calibration-json", str(calibration)]) == 0
    assert json.loads(capsys.readouterr().out)["rgb_orthophoto_verified"] is False
