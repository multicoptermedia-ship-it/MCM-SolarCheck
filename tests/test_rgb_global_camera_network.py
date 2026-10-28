"""Multi-frame synthetic 3D survey-free camera network tests.

Pixel correspondences are generated mathematically from 3D points. This
tests the spatial SfM initializer, not just a pair homography.
"""
import numpy as np
import pytest
import cv2
from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_global_camera_network import (
    RGBNetworkFrame,RGBNetworkLink,solve_global_rgb_camera_network,
)


def synthetic_observations(count=4):
    rng=np.random.default_rng(20261028)
    xyz=np.column_stack((
        rng.uniform(-2.2,2.2,90),
        rng.uniform(-1.5,1.5,90),
        rng.uniform(6.0,12.0,90),
    ))
    k=PinholeIntrinsics(740.,740.,400.,300.)
    frames=[]
    for i in range(count):
        translation=np.array((-.65*i,0.03*i,0.))
        camera=xyz+translation
        xy=np.column_stack((k.fx*camera[:,0]/camera[:,2]+k.cx,
                            k.fy*camera[:,1]/camera[:,2]+k.cy))
        xy+=rng.normal(0,.10,xy.shape)
        frames.append(RGBNetworkFrame(f"frame-{i}",xy.astype(np.float64)))
    edges=[]
    for i in range(count):
        for j in range(i+1,min(count,i+3)):
            edges.append(RGBNetworkLink(
                f"frame-{i}",f"frame-{j}",
                np.array([(index,index) for index in range(len(xyz))],np.int32),
            ))
    return tuple(frames),tuple(edges),k


def test_four_real_3d_views_form_one_global_camera_and_landmark_network():
    frames,links,k=synthetic_observations()
    result=solve_global_rgb_camera_network(frames,links,k)
    assert result.frame_ids==tuple(f.frame_id for f in frames)
    assert len(result.world_to_camera)==4
    assert result.reconstructed_landmarks>=12
    assert result.multiview_tracks>=12
    assert result.linked_image_pairs>=3
    assert result.reprojection_p95_px < 2.
    assert all(np.isfinite(pose).all() and pose.shape==(3,4)
               for pose in result.world_to_camera)
    assert not result.metric_scale_verified
    assert not result.roof_geometry_verified
    assert not result.orthophoto_verified
    assert not result.bundle_adjustment_completed


def test_disconnected_fourth_image_must_not_be_accepted_as_a_full_network():
    frames,links,k=synthetic_observations()
    edges=tuple(l for l in links if l.second_id!="frame-3")
    with pytest.raises(ValueError,match="disconnected|underconstrained"):
        solve_global_rgb_camera_network(frames,edges,k)


def test_false_missing_intrinsics_and_insufficient_shared_tracks_fail():
    frames,links,k=synthetic_observations()
    with pytest.raises(ValueError,match="calibrated camera intrinsics"):
        solve_global_rgb_camera_network(frames,links,PinholeIntrinsics(0,740,400,300))
    with pytest.raises(ValueError,match="network|tracks|calibrated"):
        solve_global_rgb_camera_network(frames[:3],(),k)


def test_duplicate_frame_and_oversized_feature_matches_fail_closed():
    frames,links,k=synthetic_observations()
    invalid=(frames[0],frames[0],frames[2])
    with pytest.raises(ValueError,match="unique"):
        solve_global_rgb_camera_network(invalid,links,k)
    with pytest.raises(ValueError,match="correspondence"):
        bad=RGBNetworkLink(links[0].first_id,links[0].second_id,np.full((90,2),9999,np.int32))
        solve_global_rgb_camera_network(frames,(bad,)+links[1:],k)
