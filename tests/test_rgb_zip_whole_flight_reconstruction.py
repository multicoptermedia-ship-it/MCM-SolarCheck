"""Private RGB ZIP -> full 12-frame feature/RTK/BA handoff; synthetic only."""
from io import BytesIO
from dataclasses import replace
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest
from PIL import Image

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import RGBWindowedBAResult
from mcm_solarcheck.services.rgb_flight_zip_series import read_private_rgb_zip_series
from mcm_solarcheck.services import rgb_zip_whole_flight_reconstruction as process
from mcm_solarcheck.services.rgb_zip_whole_flight_cli import main


def _jpg(number):
    out = BytesIO()
    Image.new("RGB", (400, 300), (60, 80, 100)).save(out, format="JPEG")
    xmp = (f'''<?xpacket begin=" "/><x:xmpmeta xmlns:x="adobe:ns:meta/"
        xmlns:drone-dji="http://www.dji.com/drone-dji/1.0/"
        drone-dji:GpsLatitude="{50+number*.00001:.8f}"
        drone-dji:GpsLongitude="{7+(number%4)*.00002:.8f}"
        drone-dji:AbsoluteAltitude="+111.22"
        drone-dji:GimbalYawDegree="2.0"
        drone-dji:GimbalPitchDegree="-90.0"
        drone-dji:GimbalRollDegree="0.0"
        drone-dji:FlightYawDegree="3.0"
        drone-dji:FlightPitchDegree="0.0"
        drone-dji:FlightRollDegree="0.0"
        drone-dji:GpsStatus="50" drone-dji:AltitudeType="RtkAlt"
        drone-dji:RtkStdLat="0.012" drone-dji:RtkStdLon="0.013"
        drone-dji:RtkStdHgt="0.023"
        drone-dji:DewarpData="0,0,0"/></x:xmpmeta>''').encode("utf-8")
    segment = bytes((0xff, 0xe1)) + (len(xmp)+2).to_bytes(2, "big") + xmp
    jpeg = out.getvalue()
    return jpeg[:2] + segment + jpeg[2:]


def _fixture(tmp_path):
    archives = [tmp_path / "RGB7.zip", tmp_path / "RGB2.tip"]
    for archive_index, archive in enumerate(archives):
        with ZipFile(archive, "w") as z:
            for n in range(1+6*archive_index, 7+6*archive_index):
                z.writestr(f"flight/DJI_20260825120000_{n:04d}_V.JPG", _jpg(n))
    camera = {
        "schema": "mcm.rgb_camera_intrinsics_external.v1",
        "lens_calibration_verified": True,
        "calibration_provenance": "independent synthetic test calibration",
        "intrinsics": {"fx": 740, "fy": 740, "cx": 200, "cy": 150},
        "distortion_coefficients": [0, 0, 0, 0, 0],
    }
    return tuple(archives), camera


def _stub_pipeline(monkeypatch, traced, *, accepted_nonadjacent=True):
    from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import RGBWindowedBAResult

    rng = np.random.default_rng(20261028)
    descriptors = rng.integers(0, 255, size=(32,32), dtype=np.uint8)
    class Point:
        def __init__(self, x, y):
            self.pt = (x, y)
    class ORB:
        def detectAndCompute(self, image, mask):
            traced.append(("decoded", image.shape))
            return ([Point(float(30 + j*8), float(40 + j*4))
                     for j in range(32)], descriptors.copy())
    monkeypatch.setattr(process.cv2, "ORB_create", lambda **k: ORB())

    def fake_global(frames, links, intrinsics, **kwargs):
        traced.append(("sfm", len(frames), len(links)))
        assert len(frames) == 12
        assert len(links) >= 11
        assert tuple(f.frame_id for f in frames) == tuple(
            f"V-{i:04d}" for i in range(1, 13)
        )
        poses = tuple(
            np.column_stack((np.eye(3), np.array([-.1*i, 0., 0.])))
            for i in range(12)
        )
        return RGBUnscaledNetwork(
            tuple(f.frame_id for f in frames), poses,
            16, 16, len(links), .7, 1.1,
            landmark_xyz_unit_baseline=np.ones((16,3), np.float64),
            observation_frame_indices=np.zeros(32, np.int32),
            observation_landmark_indices=np.tile(
                np.arange(16, dtype=np.int32), 2,
            ),
            observation_pixels_xy=np.ones((32,2), np.float64),
            accepted_link_pairs=tuple(
                (link.first_id, link.second_id) for link in links
                if accepted_nonadjacent or abs(
                    int(link.first_id[2:])-int(link.second_id[2:])
                ) == 1
            ),
        )
    monkeypatch.setattr(process, "solve_global_rgb_camera_network", fake_global)

    def fake_unscaled(network, intrinsics, **kwargs):
        traced.append(("windowed", len(network.frame_ids)))
        return RGBWindowedBAResult(
            network.world_to_camera, network.landmark_xyz_unit_baseline,
            1.2, .7, 2., 1., 12, 16, 32, 3, 6,
        )
    monkeypatch.setattr(
        process, "adjust_windowed_unscaled_rgb_network", fake_unscaled,
    )

    class MetricCandidate:
        total_cameras = 12
        def privacy_safe_summary(self):
            return {
                "camera_count": 12, "rtk_holdout_p95_m": .08,
                "roof_geometry_verified": False,
                "orthophoto_verified": False,
            }
    def fake_rtk(network, unscaled, priors, intrinsics, **kwargs):
        assert kwargs["enforce_camera_p95"] is True
        traced.append(("rtk", len(priors.frame_ids)))
        assert priors.frame_ids == network.frame_ids
        assert priors.camera_enu_m.shape == (12, 3)
        assert np.all(priors.sigma_enu_m[:, :2] >= .10)
        return MetricCandidate()
    monkeypatch.setattr(
        process, "adjust_rgb_windowed_bundle_with_private_rtk", fake_rtk,
    )


def test_private_zip_rgb_pipeline_uses_all_frames_without_extracting(tmp_path, monkeypatch):
    archives, camera = _fixture(tmp_path)
    before = [a.read_bytes() for a in archives]
    traced = []
    _stub_pipeline(monkeypatch, traced)
    result = process.reconstruct_private_complete_rgb_zip_flight(
        archives, camera, max_side=400, max_features=500,
    )
    report = result.privacy_safe_summary()
    assert report["frame_count"] == 12
    assert report["feature_matched_pairs"] >= 11
    assert report["cross_strip_matched_pairs"] > 0
    assert report["cross_strip_matches_are_descriptor_only"] is True
    assert report["sfm_accepted_spatial_nonadjacent_pairs"] >= 2
    assert report["sfm_geometric_nonadjacent_supported_cameras"] >= 3
    assert report["sfm_graph_connected"] is True
    assert report["sfm_graph_min_camera_degree"] >= 1
    assert report["physical_flight_strip_identity_verified"] is False
    assert report["physical_cross_strip_identity_verified"] is False
    assert report["all_input_rgb_frames_processed"] is True
    assert report["rgb_orthophoto_verified"] is False
    assert len([x for x in traced if x[0] == "decoded"]) == 12
    assert traced[-3:] == [
        ("sfm", 12, result.feature_matched_pair_count),
        ("windowed", 12), ("rtk", 12),
    ]
    output = json.dumps(report)
    for private in ("50.00001", "7.00002", "DJI_", "RGB7.zip",
                    "flight/", "RtkAlt", "private/"):
        assert private not in output
    assert [a.read_bytes() for a in archives] == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["RGB2.tip", "RGB7.zip"]


def test_cli_writes_only_aggregate_and_never_changes_private_jpegs(tmp_path, monkeypatch, capsys):
    archives, camera = _fixture(tmp_path)
    original = [a.read_bytes() for a in archives]
    traced = []
    _stub_pipeline(monkeypatch, traced)
    calibration = tmp_path / "lens.json"
    calibration.write_text(json.dumps(camera), encoding="utf-8")
    report_dir = tmp_path / "local_output"
    report_dir.mkdir()
    report = report_dir / "flight-summary.json"
    args = [
        "--rgb-archive", str(archives[0]),
        "--rgb-archive", str(archives[1]),
        "--calibration-json", str(calibration),
        "--report", str(report), "--max-side", "400",
        "--max-features", "500",
        "--expected-frames", "12", "--expected-archives", "2",
    ]
    assert main(args) == 0
    output = report.read_text(encoding="utf-8")
    assert json.loads(output)["frame_count"] == 12
    assert "RtkAlt" not in output
    assert "50.00001" not in output
    assert "7.00002" not in output
    assert "flight/" not in capsys.readouterr().out
    assert [a.read_bytes() for a in archives] == original
    with pytest.raises(ValueError, match="new local report"):
        main(args)


def test_missing_external_calibration_blocks_real_rgb_sfm(tmp_path, capsys):
    archives, camera = _fixture(tmp_path)
    camera["lens_calibration_verified"] = False
    evidence = tmp_path / "invalid.json"
    evidence.write_text(json.dumps(camera), encoding="utf-8")
    status = main([
        "--rgb-archive", str(archives[0]),
        "--rgb-archive", str(archives[1]),
        "--calibration-json", str(evidence),
        "--expected-frames", "12", "--expected-archives", "2",
    ])
    assert status == 2
    result = json.loads(capsys.readouterr().out)
    assert result["failed_stage"] == "calibration"
    assert result["rgb_orthophoto_verified"] is False


def test_blank_real_jpeg_fails_closed_without_any_partial_report(tmp_path):
    archives, camera = _fixture(tmp_path)
    with pytest.raises(process.PrivateRGBFlightStageError) as info:
        process.reconstruct_private_complete_rgb_zip_flight(
            archives, camera, max_side=400, max_features=500,
        )
    assert info.value.stage == "feature_extraction"
    assert len(list(tmp_path.iterdir())) == 2


def test_nonadjacent_rtk_cross_strip_candidates_are_proposed():
    ids = tuple(f"V-{i:04d}" for i in range(1, 13))
    xyz = np.array([[i*.6, (i%4)*.4, 0.] for i in range(12)])
    pairs = process._private_rgb_overlap_pairs(
        ids, xyz, max_neighbours=5,
    )
    assert len([p for p in pairs if p.reason == "consecutive"]) == 11
    assert len([p for p in pairs if p.reason == "cross_strip"]) >= 5
    assert len({frozenset((p.first_id, p.second_id)) for p in pairs}) == len(pairs)


def test_descriptor_only_spatial_links_are_not_geometry_evidence(tmp_path, monkeypatch):
    archives, camera = _fixture(tmp_path)
    seen = []
    # BFMatcher matches all of the synthetic descriptor arrays, but the fake
    # SfM solver accepts ONLY sequential pairs geometrically. The complete
    # flight gate must FAIL CLOSED before any RTK BA.
    _stub_pipeline(monkeypatch, seen, accepted_nonadjacent=False)
    with pytest.raises(process.PrivateRGBFlightStageError) as error:
        process.reconstruct_private_complete_rgb_zip_flight(
            archives, camera, max_side=400, max_features=500,
        )
    assert error.value.stage == "global_sfm"
    assert any(stage[0] == "sfm" for stage in seen)
    assert not any(stage[0] == "rtk" for stage in seen)
    assert "flight/" not in str(error.value)


def test_complete_flight_gate_rejects_partial_archives_before_feature_work(tmp_path, monkeypatch):
    archives, camera = _fixture(tmp_path)
    def must_not_extract(*args, **kwargs):
        raise AssertionError("ORB feature decode must not start for partial flight")
    monkeypatch.setattr(process, "_orb_from_private_zip", must_not_extract)
    with pytest.raises(process.PrivateRGBFlightStageError) as error:
        process.reconstruct_private_complete_rgb_zip_flight(
            archives, camera, max_side=400, max_features=500,
            expected_frame_count=160, expected_archive_count=6,
        )
    assert error.value.stage == "intake"
    with pytest.raises(process.PrivateRGBFlightStageError) as error:
        process.reconstruct_private_complete_rgb_zip_flight(
            archives, camera, max_side=400, max_features=500,
            expected_frame_count=12, expected_archive_count=3,
        )
    assert error.value.stage == "intake"


def test_exact_counter_gate_rejects_gaps_substitutions_and_unsafe_expectation(tmp_path):
    archives, _ = _fixture(tmp_path)
    series = read_private_rgb_zip_series(archives)
    assert process._check_expected_rgb_flight(
        series, expected_frame_count=12,
        expected_archive_count=2, first_counter=1,
    )
    assert not process._check_expected_rgb_flight(
        series, expected_frame_count=None,
        expected_archive_count=None, first_counter=1,
    )
    altered = replace(series, frames=tuple(
        replace(f, frame_id="V-0900") if i == 6 else f
        for i, f in enumerate(series.frames)
    ))
    with pytest.raises(ValueError, match="archive/count/counter"):
        process._check_expected_rgb_flight(
            altered, expected_frame_count=12,
            expected_archive_count=2, first_counter=1,
        )
    with pytest.raises(ValueError, match="together"):
        process._check_expected_rgb_flight(
            series, expected_frame_count=12,
            expected_archive_count=None, first_counter=1,
        )
    with pytest.raises(ValueError, match="bounded"):
        process._check_expected_rgb_flight(
            series, expected_frame_count=12,
            expected_archive_count=2, first_counter=10000,
        )


def test_offline_cli_defaults_to_full_160_and_six_archives(tmp_path, capsys):
    archives, camera = _fixture(tmp_path)
    calibration = tmp_path / "lens.json"
    calibration.write_text(json.dumps(camera), encoding="utf-8")
    status = main([
        "--rgb-archive", str(archives[0]),
        "--rgb-archive", str(archives[1]),
        "--calibration-json", str(calibration),
    ])
    assert status == 2
    report = json.loads(capsys.readouterr().out)
    assert report["failed_stage"] == "intake"
    assert report["rgb_orthophoto_verified"] is False
    assert "DJI_" not in json.dumps(report)
