"""Bounded whole-camera-network BA: synthetic 14-view 3D scene, no customer files."""
from dataclasses import replace
import json
import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
from mcm_solarcheck.services.rgb_windowed_bundle_adjustment import (
    adjust_windowed_unscaled_rgb_network,
)


def _synthetic_network(count=14,points=28):
    rng=np.random.default_rng(154)
    intrinsics=PinholeIntrinsics(700.,700.,400.,300.)
    xyz=np.column_stack((
        rng.uniform(-1.8,1.8,points),
        rng.uniform(-1.4,1.4,points),
        rng.uniform(5.,10.,points),
    ))
    ids=[];frames=[];pixels=[];cameras=[]
    for i in range(count):
        translation=np.array((-.15*i,0.,0.))
        camera=xyz+translation
        image=np.column_stack((700*camera[:,0]/camera[:,2]+400,
                               700*camera[:,1]/camera[:,2]+300))
        image+=rng.normal(0,.10,image.shape)
        for j in range(points):
            ids.append(j);frames.append(i);pixels.append(image[j])
        pose=np.column_stack((np.eye(3),translation))
        if i>=2:
            pose[:,3]+=rng.normal(0,.005,3)
        cameras.append(pose)
    noisy=xyz+rng.normal(0,.015,xyz.shape)
    return RGBUnscaledNetwork(
        tuple(f"rgb-{i}" for i in range(count)),tuple(cameras),
        points,points,count-1,1.,2.,
        landmark_xyz_unit_baseline=noisy,
        observation_landmark_indices=np.array(ids,np.int32),
        observation_frame_indices=np.array(frames,np.int32),
        observation_pixels_xy=np.array(pixels,np.float64),
    ),intrinsics


def test_entire_fourteen_camera_network_is_refined_without_frame_sampling():
    network,k=_synthetic_network()
    old_points=network.landmark_xyz_unit_baseline.copy()
    old_poses=[p.copy() for p in network.world_to_camera]
    progress=[]
    result=adjust_windowed_unscaled_rgb_network(
        network,k,window_cameras=6,overlap_cameras=2,
        max_iterations=5,on_progress=lambda *v:progress.append(v),
    )
    assert result.camera_count==14
    assert result.observation_count==14*28
    assert result.completed_windows==3
    assert len(progress)==3
    assert progress[-1][0]==3
    assert result.after_rmse_px <= result.before_rmse_px + 1e-8
    assert not result.metric_scale_verified
    assert not result.georeferencing_verified
    assert not result.global_joint_ba_completed
    assert not result.orthophoto_verified
    np.testing.assert_allclose(result.world_to_camera[0],old_poses[0])
    np.testing.assert_allclose(result.world_to_camera[1],old_poses[1])
    assert not np.allclose(old_points,result.landmark_xyz_unit_baseline)
    np.testing.assert_allclose(network.landmark_xyz_unit_baseline,old_points)
    for i,p in enumerate(network.world_to_camera):
        np.testing.assert_allclose(p,old_poses[i])


def test_unconnected_window_never_returns_silent_partial_flight():
    network,k=_synthetic_network()
    f=network.observation_frame_indices.copy()
    # Camera 13 has no supporting observations; do not silently skip it.
    f=f[f!=13]
    ids=network.observation_landmark_indices[:len(f)]
    pixels=network.observation_pixels_xy[:len(f)]
    broken=replace(network,observation_frame_indices=f,
                   observation_landmark_indices=ids,observation_pixels_xy=pixels)
    with pytest.raises(ValueError,match="complete|insufficient|invalid"):
        adjust_windowed_unscaled_rgb_network(broken,k)


def test_resource_budget_and_cancellation_are_explicit():
    network,k=_synthetic_network()
    with pytest.raises(ValueError,match="budget"):
        adjust_windowed_unscaled_rgb_network(network,k,max_cameras_total=12)
    with pytest.raises(RuntimeError,match="cancelled"):
        adjust_windowed_unscaled_rgb_network(network,k,should_cancel=lambda:True)


def test_no_3d_geometry_can_be_faked_from_partial_observations():
    network,k=_synthetic_network()
    with pytest.raises(ValueError,match="invalid|complete"):
        adjust_windowed_unscaled_rgb_network(
            replace(network,observation_landmark_indices=np.full(
                len(network.observation_landmark_indices),9999,np.int32)),k,
        )


def test_unscaled_npz_to_windowed_ba_cli_is_offline_and_nonmetric(tmp_path,capsys):
    """The existing SfM NPZ can be optimized without opening photos again."""
    from mcm_solarcheck.services.rgb_windowed_bundle_adjustment_cli import main

    network,k=_synthetic_network()
    source=tmp_path/"rgb-global-camera-network-unscaled.npz"
    with source.open("xb") as fp:
        np.savez_compressed(
            fp,
            poses_world_to_camera_arbitrary=np.stack(network.world_to_camera),
            landmarks_xyz_arbitrary=network.landmark_xyz_unit_baseline,
            observation_landmark_indices=network.observation_landmark_indices,
            observation_frame_indices=network.observation_frame_indices,
            observation_pixels_xy=network.observation_pixels_xy,
            calibrated_intrinsics=np.array([k.fx,k.fy,k.cx,k.cy]),
        )
    summary_path=tmp_path/"rgb-global-camera-network-unscaled.json"
    summary_path.write_text(json.dumps({
        "schema":"mcm.rgb_global_camera_network.v1",
        "unscaled_track_bundle":source.name,
        "metric_scale_verified":False,
        "orthophoto_verified":False,
        "bundle_adjustment_completed":False,
        "camera_frame_ids":list(network.frame_ids),
    }),encoding="utf-8")
    original=source.read_bytes()
    folder=tmp_path/"result"
    folder.mkdir()
    assert main([
        "--source-npz",str(source),
        "--source-json",str(summary_path),
        "--output-directory",str(folder),
    ])==0
    assert source.read_bytes()==original
    results=json.loads((folder/"rgb-global-windowed-ba-unscaled.json").read_text(encoding="utf-8"))
    assert results["camera_count"]==14
    assert results["window_count"]==3
    assert results["metric_scale_verified"] is False
    assert results["global_joint_ba_completed"] is False
    assert results["orthophoto_verified"] is False
    with np.load(folder/results["result_npz"],allow_pickle=False) as exported:
        assert exported["poses_world_to_camera_arbitrary"].shape==(14,3,4)
        assert exported["landmarks_xyz_arbitrary"].shape==(28,3)
    assert "orthophoto_verified" in capsys.readouterr().out


def test_source_manifest_that_claims_metric_evidence_is_rejected(tmp_path):
    from mcm_solarcheck.services.rgb_windowed_bundle_adjustment_cli import main
    folder=tmp_path/"empty"
    folder.mkdir()
    source=tmp_path/"fake.npz"
    np.savez_compressed(source,invalid=np.array([1]))
    metadata=tmp_path/"fake.json"
    metadata.write_text(json.dumps({
        "schema":"mcm.rgb_global_camera_network.v1",
        "unscaled_track_bundle":source.name,
        "metric_scale_verified":True,
        "orthophoto_verified":False,
        "bundle_adjustment_completed":False,
    }),encoding="utf-8")
    with pytest.raises(ValueError,match="unscaled"):
        main([
            "--source-npz",str(source),
            "--source-json",str(metadata),
            "--output-directory",str(folder),
        ])
    assert not list(folder.iterdir())
