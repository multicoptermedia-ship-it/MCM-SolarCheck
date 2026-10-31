"""Synthetic four-camera joint BA without any customer photo or cloud upload."""
import numpy as np
import pytest
import cv2
from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_global_camera_network import RGBUnscaledNetwork
from mcm_solarcheck.services.rgb_global_bundle_adjustment import adjust_unscaled_rgb_bundle


def _network(seed=15):
    rng=np.random.default_rng(seed)
    k=PinholeIntrinsics(700.,700.,400.,300.)
    xyz=np.column_stack((rng.uniform(-2,2,24),rng.uniform(-1.5,1.5,24),
                         rng.uniform(5,11,24)))
    poses=[]
    ids=[];frames=[];px=[]
    for i in range(4):
        pose=np.column_stack((np.eye(3),np.array([-.6*i,0,0.])))
        poses.append(pose.copy())
        camera=xyz + pose[:,3]
        obs=np.column_stack((700*camera[:,0]/camera[:,2]+400,
                             700*camera[:,1]/camera[:,2]+300))
        obs+=rng.normal(0,.18,obs.shape)
        for j in range(len(xyz)):
            ids.append(j);frames.append(i);px.append(obs[j])
    noisy=xyz+rng.normal(0,.025,xyz.shape)
    poses[2][:,3]+=np.array([.025,.012,.009])
    poses[3][:,3]+=np.array([-.025,.014,-.009])
    return RGBUnscaledNetwork(
        tuple(f"frame-{i}" for i in range(4)),tuple(poses),24,24,5,1.,2.,
        landmark_xyz_unit_baseline=noisy,
        observation_landmark_indices=np.array(ids,np.int32),
        observation_frame_indices=np.array(frames,np.int32),
        observation_pixels_xy=np.array(px,np.float64),
    ),k


def test_joint_bundle_adjustment_uses_every_camera_and_reduces_error():
    network,k=_network()
    initial_poses=[p.copy() for p in network.world_to_camera]
    before_points=network.landmark_xyz_unit_baseline.copy()
    result=adjust_unscaled_rgb_bundle(network,k,max_iterations=12)
    assert result.observation_count==96
    assert result.after_rmse_px < result.before_rmse_px
    assert result.iterations>0
    assert len(result.world_to_camera)==4
    np.testing.assert_allclose(result.world_to_camera[0],initial_poses[0])
    np.testing.assert_allclose(result.world_to_camera[1],initial_poses[1])
    assert not np.allclose(result.landmark_xyz_unit_baseline,before_points)
    assert not result.metric_scale_verified
    assert not result.roof_geometry_verified
    assert not result.orthophoto_verified
    assert not np.allclose(network.landmark_xyz_unit_baseline,result.landmark_xyz_unit_baseline)
    np.testing.assert_allclose(network.world_to_camera[2],initial_poses[2])


def test_missing_tracks_resource_excess_and_cancel_fail_closed():
    network,k=_network()
    with pytest.raises(ValueError,match="budget"):
        adjust_unscaled_rgb_bundle(network,k,max_cameras=3)
    with pytest.raises(ValueError,match="observations"):
        adjust_unscaled_rgb_bundle(network,k,max_observations=24)
    with pytest.raises(RuntimeError,match="cancelled"):
        adjust_unscaled_rgb_bundle(network,k,should_cancel=lambda:True)


def test_robust_loss_rejects_nonfinite_pixel_data():
    network,k=_network()
    from dataclasses import replace
    broken=replace(network,observation_pixels_xy=np.full((96,2),np.nan))
    with pytest.raises(ValueError,match="finite"):
        adjust_unscaled_rgb_bundle(broken,k)
