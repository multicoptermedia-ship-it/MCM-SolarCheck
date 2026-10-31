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
from mcm_solarcheck.services.rgb_per_camera_reprojection_gate import (
    audit_rgb_per_camera_reprojection,
)
from mcm_solarcheck.services.rgb_multiview_parallax_gate import (
    audit_rgb_multiview_parallax,
)
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
            # A successful synthetic SfM stub must represent real shared
            # multiview 3D IDs across all 12 cameras, not one camera only.
            observation_frame_indices=np.repeat(
                np.arange(12, dtype=np.int32), 16,
            ),
            observation_landmark_indices=np.tile(
                np.arange(16, dtype=np.int32), 12,
            ),
            observation_pixels_xy=np.ones((192,2), np.float64),
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
            1.2, .7, 2., 1., 12, 16, 192, 3, 6,
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
        assert kwargs["enforce_parallax"] is True
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
    assert report["sfm_3d_track_graph_connected"] is True
    assert report["sfm_3d_supported_spatial_nonadjacent_pairs"] >= 2
    assert report["sfm_3d_min_shared_landmarks_supported_edge"] >= 8
    assert report["sfm_track_conflicting_merges_rejected"] == 0
    assert report["sfm_accepted_geometric_feature_correspondences"] == 0
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




def test_full_flight_orb_reuses_one_readonly_zip_handle_per_archive(
    tmp_path, monkeypatch,
):
    """Interleaved 12-flight RGB frames need two archive opens, not twelve.

    All handles must close on normal return AND during an interrupted
    feature pass. There is no archive extraction, copy or private output.
    """
    archives, calibration = _fixture(tmp_path)
    originals = tuple(archive.read_bytes() for archive in archives)
    flight = read_private_rgb_zip_series(archives)
    # Deliberately interleave the two source archives in the flight order.
    frames = flight.frames
    series = replace(
        flight, frames=tuple(value for pair in zip(frames[:6],frames[6:])
                             for value in pair),
    )
    source = process.ZipFile
    opened = []
    def tracked(path, *args, **kwargs):
        handle = source(path, *args, **kwargs)
        opened.append(handle)
        return handle

    _stub_pipeline(monkeypatch, [])
    monkeypatch.setattr(process,"ZipFile",tracked)
    intrinsics = PinholeIntrinsics(740.,740.,200.,150.)
    distortion = np.zeros(5,dtype=np.float64)
    frames_out,desc = process._orb_from_private_zip(
        series,intrinsics,distortion,max_side=400,max_features=500,
        should_cancel=None,on_progress=None,
    )
    assert len(frames_out) == len(desc) == 12
    assert len(opened) == len(archives)
    assert all(handle.fp is None for handle in opened)
    assert tuple(archive.read_bytes() for archive in archives) == originals

    opened.clear()
    def interrupt(stage,done,total):
        if done == 3:
            raise RuntimeError("synthetic feature interruption")
    with pytest.raises(RuntimeError,match="synthetic feature interruption"):
        process._orb_from_private_zip(
            series,intrinsics,distortion,max_side=400,max_features=500,
            should_cancel=None,on_progress=interrupt,
        )
    assert len(opened) == len(archives)
    assert all(handle.fp is None for handle in opened)
    assert tuple(archive.read_bytes() for archive in archives) == originals
    assert sorted(p.name for p in tmp_path.iterdir()) == ["RGB2.tip","RGB7.zip"]

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


def test_cli_strict_pixel_failure_preserves_only_aggregate_camera_metrics(
    tmp_path, monkeypatch, capsys,
):
    archives, camera = _fixture(tmp_path)
    originals = [path.read_bytes() for path in archives]
    _stub_pipeline(monkeypatch, [])
    def fail_camera_p95(network, windowed, priors, intrinsics, **kwargs):
        assert kwargs["enforce_camera_p95"] is True
        # Synthetic fitted 12-camera geometry: all images see multiple shared
        # 3D points, with exactly one corrupted camera at the final gate.
        poses = tuple(
            np.column_stack((np.eye(3), np.array([-.02*i, 0., 0.])))
            for i in range(12)
        )
        xyz = np.column_stack((
            np.linspace(-1., 1., 12), np.zeros(12), np.full(12, 10.)
        ))
        fid = np.repeat(np.arange(12, dtype=np.int32), 12)
        lid = np.tile(np.arange(12, dtype=np.int32), 12)
        cam_xyz = xyz[lid] + np.asarray(poses)[fid, :, 3]
        xy = np.column_stack((
            intrinsics.fx*cam_xyz[:, 0]/cam_xyz[:, 2]+intrinsics.cx,
            intrinsics.fy*cam_xyz[:, 1]/cam_xyz[:, 2]+intrinsics.cy,
        ))
        xy[fid == 5, 0] += 25.
        return audit_rgb_per_camera_reprojection(
            poses, xyz, fid, lid, xy, intrinsics,
            enforce_camera_p95=kwargs["enforce_camera_p95"],
        )
    monkeypatch.setattr(
        process, "adjust_rgb_windowed_bundle_with_private_rtk",
        fail_camera_p95,
    )
    calibration = tmp_path / "lens.json"
    calibration.write_text(json.dumps(camera), encoding="utf-8")
    local = tmp_path / "private_report"
    local.mkdir()
    target = local / "reconstruction-failed.json"
    argv = [
        "--rgb-archive", str(archives[0]),
        "--rgb-archive", str(archives[1]),
        "--calibration-json", str(calibration),
        "--report", str(target),
        "--max-side", "400", "--max-features", "500",
        "--expected-frames", "12", "--expected-archives", "2",
    ]
    assert main(argv) == 2
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report == json.loads(capsys.readouterr().out)
    assert report["status"] == "whole_flight_rgb_quality_gate_failed"
    assert report["failed_stage"] == "rtk_weighted_ba"
    audit = report["per_camera_reprojection"]
    assert audit["cameras_above_p95_limit"] == 1
    assert audit["camera_p95_limit_px"] == 6.
    assert audit["worst_camera_reprojection_p95_px"] >= 20.
    assert audit["camera_reprojection_quality_passed"] is False
    assert report["rgb_orthophoto_verified"] is False
    assert report["all_input_rgb_frames_processed"] is False
    for private in ("DJI_", "RGB2.tip", "RGB7.zip", "flight/",
                    "V-0006", "latitude", "longitude", "50.00001",
                    "7.00002", "path", "private/"):
        assert private not in target.read_text(encoding="utf-8")
    assert [p.read_bytes() for p in archives] == originals
    assert list(local.iterdir()) == [target]


def test_private_zip_cli_rejects_weak_multiview_depth_and_reports_only_angles(
    tmp_path, monkeypatch, capsys,
):
    archives, camera = _fixture(tmp_path)
    originals = [archive.read_bytes() for archive in archives]
    _stub_pipeline(monkeypatch, [])
    def weak_parallax(network, unscaled, priors, intrinsics, **kwargs):
        assert kwargs["enforce_camera_p95"] is True
        assert kwargs["enforce_parallax"] is True
        poses = tuple(
            np.column_stack((np.eye(3), np.array((-1e-5*i, 0., 0.))))
            for i in range(12)
        )
        xyz = np.column_stack((
            np.linspace(-1., 1., 16), np.zeros(16), np.full(16, 10.)
        ))
        fid = np.repeat(np.arange(12, dtype=np.int32), 16)
        lid = np.tile(np.arange(16, dtype=np.int32), 12)
        return audit_rgb_multiview_parallax(
            poses, xyz, fid, lid, enforce_parallax=kwargs["enforce_parallax"],
        )
    monkeypatch.setattr(
        process, "adjust_rgb_windowed_bundle_with_private_rtk", weak_parallax,
    )
    calibration = tmp_path / "lens.json"
    calibration.write_text(json.dumps(camera), encoding="utf-8")
    local = tmp_path / "output"
    local.mkdir()
    target = local / "failed-parallax.json"
    args = [
        "--rgb-archive", str(archives[0]),
        "--rgb-archive", str(archives[1]),
        "--calibration-json", str(calibration),
        "--report", str(target),
        "--max-side", "400", "--max-features", "500",
        "--expected-frames", "12", "--expected-archives", "2",
    ]
    assert main(args) == 2
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report == json.loads(capsys.readouterr().out)
    assert report["status"] == "whole_flight_rgb_quality_gate_failed"
    assert report["failed_stage"] == "rtk_weighted_ba"
    assert report["multiview_parallax"]["parallax_quality_passed"] is False
    assert report["multiview_parallax"]["weak_landmark_count"] == 16
    assert report["multiview_parallax"]["roof_geometry_verified"] is False
    assert report["rgb_orthophoto_verified"] is False
    assert report["all_input_rgb_frames_processed"] is False
    content = target.read_text(encoding="utf-8")
    for secret in ("DJI_", "RGB2.tip", "RGB7.zip", "flight/", "V-0006",
                   "latitude", "longitude", "path", "private/"):
        assert secret not in content
    assert [archive.read_bytes() for archive in archives] == originals


def test_geometry_only_spatial_links_cannot_pass_without_shared_3d_points(
    tmp_path, monkeypatch,
):
    archives, camera = _fixture(tmp_path)
    seen = []
    _stub_pipeline(monkeypatch, seen)
    original_solver = process.solve_global_rgb_camera_network

    def geometrically_accepted_but_disconnected_tracks(*args, **kwargs):
        network = original_solver(*args, **kwargs)
        # Each adjacent camera pair sees 8 genuine common 3D points.
        # Their landmark IDs are private, unique to that adjacent pair:
        # only sequential links have shared 3D support. All essential
        # spatial links still claim geometry acceptance in this stub.
        fid, lid = [], []
        for i in range(11):
            for p in range(8):
                for camera_id in (i, i+1):
                    fid.append(camera_id)
                    lid.append(8*i+p)
        return replace(
            network,
            reconstructed_landmarks=88,
            landmark_xyz_unit_baseline=np.ones((88, 3), dtype=np.float64),
            observation_frame_indices=np.asarray(fid, dtype=np.int32),
            observation_landmark_indices=np.asarray(lid, dtype=np.int32),
            observation_pixels_xy=np.ones((len(fid), 2), dtype=np.float64),
        )

    monkeypatch.setattr(
        process, "solve_global_rgb_camera_network",
        geometrically_accepted_but_disconnected_tracks,
    )
    with pytest.raises(process.PrivateRGBFlightStageError) as error:
        process.reconstruct_private_complete_rgb_zip_flight(
            archives, camera, max_side=400, max_features=500,
        )
    assert error.value.stage == "global_sfm"
    assert any(stage[0] == "sfm" for stage in seen)
    assert not any(stage[0] in ("windowed", "rtk") for stage in seen)
    assert "V-0001" not in str(error.value)


def test_opt_in_original_zip_rgb_to_fitted_pitched_plane_preview_read_only(
    tmp_path, monkeypatch,
):
    """Actual synthetic ZIP/JPEG decode+distortion+project, no stubbed remap."""
    from mcm_solarcheck.services.rgb_rtk_joint_bundle_adjustment import (
        PrivateRGBRTKWindowedBA,
    )
    from mcm_solarcheck.services.rgb_per_camera_reprojection_gate import (
        RGBPerCameraReprojectionAudit,
    )
    from mcm_solarcheck.services.rgb_multiview_parallax_gate import (
        RGBMultiviewParallaxAudit,
    )
    from mcm_solarcheck.services.rgb_private_pitched_plane_candidates import (
        PrivateRGBPitchedPlaneCandidate, PrivateRGBPitchedPlaneCandidates,
    )
    archives, camera = _fixture(tmp_path)
    original = tuple(path.read_bytes() for path in archives)
    n = np.array((-.2,0.,1.), dtype=np.float64)
    n /= np.linalg.norm(n)
    plane = PrivateRGBPitchedPlaneCandidate(
        n, -1./np.sqrt(1.04), np.arange(32, dtype=np.int32),
        np.array([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]]),
        11.3, 4, .01, 1.,
    )
    poses = []
    r = np.diag((1.,-1.,-1.))
    for i in range(12):
        center = np.array((.05*i,0.,5.))
        poses.append(np.column_stack((r,-r @ center)))
    metric = PrivateRGBRTKWindowedBA(
        tuple(f"V-{i:04d}" for i in range(1,13)), tuple(poses),
        np.zeros((32,3)), 1., .5, .1, .1, .2, 10, 2, 12, 3, 20., 10.,
        camera_reprojection_audit=RGBPerCameraReprojectionAudit(
            12,32,384,32,12,1.,1.,1.,
        ),
        multiview_parallax_audit=RGBMultiviewParallaxAudit(
            12,32,384,.25,.75,32,0,2.,3.,
        ),
        pitched_plane_candidates=PrivateRGBPitchedPlaneCandidates((plane,),32),
    )
    patch = process.render_private_pitched_preview_from_original_rgb_archives(
        archives, camera, metric, 0, (0,1), meters_per_pixel=.025,
    )
    assert patch.rgb_private.shape == (40,40,3)
    assert patch.valid_pixel_count > 1200
    assert patch.multi_camera_pixel_count == patch.valid_pixel_count
    values = patch.rgb_private[patch.valid_mask_private]
    np.testing.assert_allclose(np.median(values,axis=0),
                               (60.,80.,100.), atol=3.)
    report = patch.privacy_safe_summary()
    assert report["source_camera_count"] == 2
    assert report["orthophoto_verified"] is False
    assert "V-0001" not in json.dumps(report)
    assert "RGB2.tip" not in json.dumps(report)
    assert tuple(path.read_bytes() for path in archives) == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["RGB2.tip","RGB7.zip"]
    with pytest.raises(ValueError, match="identities differ"):
        process.render_private_pitched_preview_from_original_rgb_archives(
            archives, camera, replace(metric, frame_ids=metric.frame_ids[::-1]),
            0, (0,1),
        )
    # New vertical multi-facet path: same unchanged synthetic source ZIP
    # set, but the fitted BA camera poses select the source photos for each
    # half of the candidate pitched roof automatically.
    left = replace(
        plane,
        footprint_xy_private_m=np.array([
            [-.5,-.5], [0.,-.5], [0.,.5], [-.5,.5],
        ],dtype=np.float64),
        footprint_area_m2=.5,
    )
    right = replace(
        plane,
        footprint_xy_private_m=np.array([
            [0.,-.5], [.5,-.5], [.5,.5], [0.,.5],
        ],dtype=np.float64),
        footprint_area_m2=.5,
    )
    multi_metric = replace(
        metric, pitched_plane_candidates=PrivateRGBPitchedPlaneCandidates(
            (left,right),32,
        ),
    )
    combined = process.render_private_multiplane_preview_from_original_rgb_archives(
        archives, camera, multi_metric, meters_per_pixel=.025,
    )
    assert combined.rgb_private.shape == (40,40,3)
    assert combined.plane_count == 2
    assert combined.valid_pixel_count > 1200
    assert combined.ambiguous_overlap_pixels == 0
    assert combined.source_camera_counts[0] >= 2
    assert combined.source_camera_counts[1] >= 2
    np.testing.assert_allclose(
        np.median(combined.rgb_private[combined.valid_mask_private],axis=0),
        (60.,80.,100.), atol=3.,
    )
    assert not combined.rgb_private.flags.writeable
    assert combined.privacy_safe_summary()["orthophoto_verified"] is False
    assert "V-0001" not in json.dumps(combined.privacy_safe_summary())
    assert tuple(path.read_bytes() for path in archives) == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["RGB2.tip","RGB7.zip"]

    # Two fitted facets may choose the same real RGB stereo pair. Reuse the
    # validated in-memory flight index and each undistorted JPEG ONCE across
    # facets, rather than rescanning six ZIPs and decoding duplicate cameras.
    # The fixture is synthetic; it is not a 160-JPEG photogrammetry proof.
    from mcm_solarcheck.services import rgb_private_multi_plane_preview as compositor
    scan_calls, decode_calls = [], []
    with monkeypatch.context() as patch:
        patch.setattr(
            compositor, "choose_private_pitched_plane_cameras",
            lambda *args, **kwargs: (0, 1),
        )
        original_index = process.read_private_rgb_zip_series
        original_decode = process.cv2.imdecode

        def count_scan(*args, **kwargs):
            scan_calls.append(1)
            return original_index(*args, **kwargs)

        def count_decode(*args, **kwargs):
            decode_calls.append(1)
            return original_decode(*args, **kwargs)

        patch.setattr(process, "read_private_rgb_zip_series", count_scan)
        patch.setattr(process.cv2, "imdecode", count_decode)
        reused = process.render_private_multiplane_preview_from_original_rgb_archives(
            archives, camera, multi_metric, meters_per_pixel=.025,
        )
    assert reused.valid_pixel_count > 1200
    assert reused.privacy_safe_summary()["orthophoto_verified"] is False
    assert len(scan_calls) == 1
    assert len(decode_calls) == 2
    assert tuple(path.read_bytes() for path in archives) == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ["RGB2.tip","RGB7.zip"]

    camera["lens_calibration_verified"] = False
    with pytest.raises(ValueError, match="independent calibrated"):
        process.render_private_pitched_preview_from_original_rgb_archives(
            archives, camera, metric, 0, (0,1),
        )
    with pytest.raises(ValueError, match="independent calibrated"):
        process.render_private_multiplane_preview_from_original_rgb_archives(
            archives, camera, multi_metric,
        )
