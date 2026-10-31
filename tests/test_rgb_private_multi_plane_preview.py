"""Vertical private multi-pitched-facet RGB composition, synthetic only."""
import json
from dataclasses import replace

import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_private_pitched_plane_candidates import (
    PrivateRGBPitchedPlaneCandidate, PrivateRGBPitchedPlaneCandidates,
)
from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
    PrivateRGBPitchedPlaneOrthopatch,
)
from mcm_solarcheck.services.rgb_private_multi_plane_preview import (
    choose_private_pitched_plane_cameras,
    compose_private_pitched_rgb_orthopatches,
)
from mcm_solarcheck.services.rgb_rtk_joint_bundle_adjustment import (
    PrivateRGBRTKWindowedBA,
)
from mcm_solarcheck.services.rgb_per_camera_reprojection_gate import (
    RGBPerCameraReprojectionAudit,
)
from mcm_solarcheck.services.rgb_multiview_parallax_gate import (
    RGBMultiviewParallaxAudit,
)


def _facet(x0, x1, *, slope=0.2, rgb=(0, 0, 0)):
    n = np.array((-slope, 0., 1.), dtype=np.float64)
    n /= np.linalg.norm(n)
    hull = np.array(((x0,-1.),(x1,-1.),(x1,1.),(x0,1.)))
    return PrivateRGBPitchedPlaneCandidate(
        n, -1./np.sqrt(1+slope*slope), np.arange(32,dtype=np.int32),
        hull, float(np.degrees(np.arctan(abs(slope)))),
        4, .01, (x1-x0)*2.,
    )


def _patch(plane, value, meters_per_pixel=.1):
    hull = plane.footprint_xy_private_m
    x0 = hull[:,0].min()
    north = hull[:,1].max()
    w = int(round(np.ptp(hull[:,0])/meters_per_pixel))
    h = int(round(np.ptp(hull[:,1])/meters_per_pixel))
    rgb = np.empty((h,w,3),dtype=np.uint8)
    rgb[:,:,:] = value
    valid = np.ones((h,w),dtype=bool)
    return PrivateRGBPitchedPlaneOrthopatch(
        rgb, valid, (float(x0),float(north)), meters_per_pixel,
        3, h*w, h*w, h*w,
    )


def _poses():
    r = np.diag((1.,-1.,-1.))
    centers = ((-.6,0.,5.), (.0,0.,5.), (.6,0.,5.))
    return tuple(np.column_stack((r,-r @ np.array(c))) for c in centers)


def _metric(planes):
    poses = _poses()
    return PrivateRGBRTKWindowedBA(
        ("synthetic-0","synthetic-1","synthetic-2"),
        poses, np.zeros((32,3)), 1., .5, .1,.1,.2,
        2,1,3,3,20.,10.,
        camera_reprojection_audit=RGBPerCameraReprojectionAudit(
            3,32,96,32,3,1.,1.,1.,
        ),
        multiview_parallax_audit=RGBMultiviewParallaxAudit(
            3,32,96,.25,.75,32,0,2.,3.,
        ),
        pitched_plane_candidates=PrivateRGBPitchedPlaneCandidates(
            tuple(planes),32,
        ),
    )


def test_geometric_camera_selection_uses_real_3d_poses_and_full_image_bounds():
    k = PinholeIntrinsics(60.,60.,64.,64.)
    selected = choose_private_pitched_plane_cameras(
        _facet(-2.,0.), _poses(), k, 128,128,
    )
    assert len(selected) == 2
    assert len(set(selected)) == 2
    assert all(0 <= i < 3 for i in selected)
    bad = tuple(np.column_stack(
        (np.diag((1.,-1.,-1.)), np.array((0.,0.,-5.)))
    ) for _ in range(3))
    with pytest.raises(ValueError, match="fewer than two"):
        choose_private_pitched_plane_cameras(
            _facet(-2.,0.), bad, k, 128,128,
        )


def test_two_distinct_pitched_faces_use_one_north_up_enu_rgb_grid():
    left, right = _facet(-2.,0.), _facet(0.,2.,slope=-.25)
    fused = compose_private_pitched_rgb_orthopatches(
        (left,right),
        (_patch(left,(220,40,20)),_patch(right,(20,40,220))),
    )
    assert fused.rgb_private.shape == (20,40,3)
    assert fused.valid_pixel_count == 800
    assert fused.ambiguous_overlap_pixels == 0
    np.testing.assert_array_equal(fused.rgb_private[10,10],(220,40,20))
    np.testing.assert_array_equal(fused.rgb_private[10,30],(20,40,220))
    assert set(np.unique(fused.selected_plane_index_private)) == {0,1}
    assert fused.top_left_xy_enu_private_m == (-2.,1.)
    assert not fused.rgb_private.flags.writeable
    assert not fused.valid_mask_private.flags.writeable
    assert not fused.selected_plane_index_private.flags.writeable
    summary = fused.privacy_safe_summary()
    assert summary["plane_candidate_count"] == 2
    assert summary["orthophoto_verified"] is False
    assert summary["roof_surface_identity_verified"] is False
    for secret in ("rgb_private", "top_left_xy", "selected_plane_index",
                   "footprint", "ENU", "DJI_", "GPS"):
        assert secret not in json.dumps(summary)


def test_same_height_overlapping_3d_facets_stay_ambiguous_not_mixed():
    first, second = _facet(-1.,1.), _facet(-1.,1.)
    fused = compose_private_pitched_rgb_orthopatches(
        (first,second),
        (_patch(first,(255,0,0)),_patch(second,(0,0,255))),
    )
    assert fused.ambiguous_overlap_pixels == 400
    assert fused.valid_pixel_count == 0
    assert np.all(fused.selected_plane_index_private == -1)
    assert not np.any(fused.rgb_private)
    assert not fused.privacy_safe_summary()["orthophoto_verified"]


def test_bad_alignment_or_overbudget_grid_fails_without_writing():
    a,b = _facet(-2.,0.), _facet(0.,2.)
    p,q = _patch(a,(100,0,0)),_patch(b,(0,100,0))
    with pytest.raises(ValueError, match="share a common"):
        compose_private_pitched_rgb_orthopatches(
            (a,b),(p,replace(q,meters_per_pixel=.2)),
        )
    with pytest.raises(ValueError,match="misaligned"):
        compose_private_pitched_rgb_orthopatches(
            (a,b),(p,replace(q,top_left_xy_enu_private_m=(22.,1.))),
        )
    far = _facet(0.,10.)
    large = _patch(far,(0,100,0))
    with pytest.raises(ValueError,match="resource budget"):
        compose_private_pitched_rgb_orthopatches(
            (a,far),(p,large),max_side=64,
        )


def test_metric_ba_auto_selects_and_renders_two_facets_from_undistorted_cameras():
    k = PinholeIntrinsics(60.,60.,64.,64.)
    left,right = _facet(-1.,0.),_facet(0.,1.,slope=-.2)
    metric = _metric((left,right))
    frames = {
        0:np.full((128,128,3),(120,80,50),dtype=np.uint8),
        1:np.full((128,128,3),(120,80,50),dtype=np.uint8),
        2:np.full((128,128,3),(120,80,50),dtype=np.uint8),
    }
    original = {i:img.copy() for i,img in frames.items()}
    fused = metric.render_private_multi_plane_preview(
        frames,k,meters_per_pixel=.05,
    )
    assert fused.plane_count == 2
    assert fused.valid_pixel_count > 600
    assert np.all(fused.rgb_private[fused.valid_mask_private] == [120,80,50])
    assert fused.privacy_safe_summary()["orthophoto_verified"] is False
    assert all(np.array_equal(frames[i], original[i]) for i in frames)
    with pytest.raises(ValueError,match="complete private"):
        replace(metric,camera_reprojection_audit=None
                ).render_private_multi_plane_preview(frames,k)



def test_multiplane_composition_keeps_private_photometric_aggregate_only():
    left,right = _facet(-1.,0.),_facet(0.,1.,slope=-.2)
    a,b = _patch(left,(100,100,100)),_patch(right,(100,100,100))
    fused = compose_private_pitched_rgb_orthopatches(
        (left,right),
        (replace(a, radiometric_corrected_source_count=1,
                 radiometric_overlap_support_pixels=256),
         replace(b, radiometric_corrected_source_count=2,
                 radiometric_overlap_support_pixels=300)),
    )
    assert fused.radiometric_corrected_source_count == 3
    assert fused.radiometric_overlap_support_pixels == 556
    report = fused.privacy_safe_summary()
    assert report["radiometric_corrected_source_count"] == 3
    assert report["radiometric_overlap_support_pixels"] == 556
    assert report["orthophoto_verified"] is False
    for forbidden in ("top_left_xy","selected_plane_index","GPS","DJI_"):
        assert forbidden not in json.dumps(report)



def test_facets_color_transition_is_measured_but_not_claimed_as_quality_pass():
    first,second = _facet(-1.,0.),_facet(0.,1.,slope=-.2)
    a,b = _patch(first,(100,120,140)),_patch(second,(125,120,140))
    a = replace(a,candidate_camera_seam_boundary_pairs=25,
                candidate_camera_seam_rgb_jump_p95=13.)
    b = replace(b,candidate_camera_seam_boundary_pairs=10,
                candidate_camera_seam_rgb_jump_p95=20.)
    fused = compose_private_pitched_rgb_orthopatches(
        (first,second),(a,b),
    )
    assert fused.candidate_camera_seam_boundary_pairs == 35
    assert fused.worst_candidate_camera_seam_rgb_jump_p95 == 20.
    assert fused.candidate_facet_transition_boundary_pairs == 20
    assert fused.candidate_facet_transition_rgb_jump_p95 == 25.
    safe = fused.privacy_safe_summary()
    assert safe["candidate_facet_transition_boundary_pairs"] == 20
    assert safe["worst_candidate_camera_seam_rgb_jump_p95"] == 20.
    assert safe["roof_geometry_verified"] is False
    assert safe["orthophoto_verified"] is False
    for private in ("selected_plane_index", "camera_id", "GPS", "top_left_xy"):
        assert private not in json.dumps(safe)


def test_transparent_ambiguity_cannot_form_fake_facet_seams():
    first,second = _facet(-1.,1.),_facet(-1.,1.)
    fused = compose_private_pitched_rgb_orthopatches(
        (first,second),
        (_patch(first,(255,0,0)),_patch(second,(0,0,255))),
    )
    assert fused.valid_pixel_count == 0
    assert fused.candidate_facet_transition_boundary_pairs == 0
    assert fused.candidate_facet_transition_rgb_jump_p95 is None


def test_multiplane_reports_only_aggregate_convex_hull_extrapolation():
    first,second = _facet(-1.,0.),_facet(0.,1.,slope=-.2)
    a = replace(_patch(first,(100,120,140)),
                unsupported_convex_hull_pixels=35)
    b = replace(_patch(second,(100,120,140)),
                unsupported_convex_hull_pixels=28)
    composed = compose_private_pitched_rgb_orthopatches(
        (first,second),(a,b),
    )
    assert composed.unsupported_convex_hull_pixels == 63
    safe = composed.privacy_safe_summary()
    assert safe["unsupported_convex_hull_pixels"] == 63
    assert safe["roof_geometry_verified"] is False
    assert safe["orthophoto_verified"] is False
    for private in ("inlier_xy","landmark_indices","top_left_xy","GPS"):
        assert private not in json.dumps(safe)


def test_camera_selection_excludes_sources_hidden_by_other_pitched_facet():
    """A top-down primary fully blocked by an upper facet cannot win."""
    k = PinholeIntrinsics(60.,60.,64.,64.)
    low = _facet(-.5,.5)
    top = _facet(-.7,.7)
    # Exact same pitched plane slope shifted from z=1 to z=3.
    high = replace(top,signed_offset_enu_private_m=3*top.signed_offset_enu_private_m)
    r = np.diag((1.,-1.,-1.))
    centers = ((0.,0.,5.), (3.,0.,5.), (-3.,0.,5.))
    poses = tuple(np.column_stack((r,-r @ np.asarray(center)))
                  for center in centers)
    geometric = choose_private_pitched_plane_cameras(
        low,poses,k,128,128,max_cameras=2,
    )
    assert 0 in geometric
    visible = choose_private_pitched_plane_cameras(
        low,poses,k,128,128,max_cameras=2,
        occluder_planes=(high,),
    )
    assert set(visible) == {1,2}


def test_camera_selection_samples_actual_3d_support_not_only_convex_bbox():
    """No camera covering only the phantom convex void can be a source."""
    k = PinholeIntrinsics(200.,200.,64.,64.)
    low = _facet(-2.,2.)
    yy = np.linspace(-.95,.95,48)
    xy = np.asarray([(x,y) for x in (-1.9,1.9) for y in yy])
    low = replace(low,
        landmark_indices_private=np.arange(len(xy),dtype=np.int32),
        inlier_xy_private_m=xy,
    )
    r = np.diag((1.,-1.,-1.))
    poses = tuple(np.column_stack(
        (r,-r @ np.array((x,0.,5.)))
    ) for x in (-1.8,1.8,0.))
    chosen = choose_private_pitched_plane_cameras(
        low,poses,k,128,128,max_cameras=2,
    )
    assert set(chosen) == {0,1}
    assert len(chosen) == 2


def test_camera_selection_rejects_unknown_occluders_and_is_cancellable():
    k = PinholeIntrinsics(60.,60.,64.,64.)
    low = _facet(-2.,0.)
    with pytest.raises(ValueError,match="bounded private"):
        choose_private_pitched_plane_cameras(
            low,_poses(),k,128,128,occluder_planes=[low],
        )
    with pytest.raises(RuntimeError,match="cancelled"):
        choose_private_pitched_plane_cameras(
            low,_poses(),k,128,128,occluder_planes=(low,),
            should_cancel=lambda: True,
        )



def test_all_fitted_cameras_can_recover_visible_views_after_32_occluded_nadir(
    monkeypatch,
):
    """A 160-frame roof flight must not drop camera 33+ by RAW coverage.

    Thirty-two central cameras apparently see the entire target hull but a
    supported upper plane hides it. Two more oblique frames are genuinely
    visible; neither may be discarded before the visibility test. One
    private OpenCV support grid is reused across all candidate view rays.
    """
    from mcm_solarcheck.services import (
        rgb_private_pitched_plane_orthorectification as ortho,
    )
    low = _facet(-.5,.5)
    upper = _facet(-.7,.7)
    xx,yy = np.meshgrid(
        np.linspace(-.65,.65,11),np.linspace(-.65,.65,11),
    )
    points = np.column_stack((xx.ravel(),yy.ravel()))
    upper = replace(
        upper,
        signed_offset_enu_private_m=3*upper.signed_offset_enu_private_m,
        landmark_indices_private=np.arange(len(points),dtype=np.int32),
        inlier_xy_private_m=points,
    )
    r = np.diag((1.,-1.,-1.))
    centers = (
        [(float((i-16)*.005),0.,5.) for i in range(32)]
        + [(3.,0.,5.),(-3.,0.,5.)]
    )
    poses = tuple(np.column_stack((r,-r @ np.asarray(x)))
                  for x in centers)
    original = ortho.cv2.distanceTransform
    counter = [0]

    def counted_distance(*args,**kwargs):
        counter[0] += 1
        return original(*args,**kwargs)

    monkeypatch.setattr(ortho.cv2,"distanceTransform",counted_distance)
    visible = choose_private_pitched_plane_cameras(
        low,poses,PinholeIntrinsics(60.,60.,64.,64.),128,128,
        max_cameras=2,occluder_planes=(upper,),
    )
    assert set(visible) == {32,33}
    assert counter[0] == 1  # not 34 repeat distance transforms
    # No RGB, private 3D coords or location are serialized by selection.
    assert isinstance(visible,tuple)
    assert len(visible) == 2


def _sampling_camera_pose(x, altitude):
    r = np.diag((1.,-1.,-1.))
    center = np.array((x,0.,altitude),dtype=np.float64)
    return np.column_stack((r,-r @ center))


def test_fitted_primary_prefers_geometrically_denser_camera_on_equal_coverage():
    """A nearer fitted view should win full coverage over a far source first.

    This is a pinhole projection-density surrogate only, NOT measured RGB
    sharpness, DJI lens performance, true GSD or real roof orthorectification.
    """
    plane = _facet(-.5,.5)
    poses = (_sampling_camera_pose(0.,9.),_sampling_camera_pose(0.,5.))
    chosen = choose_private_pitched_plane_cameras(
        plane,poses,PinholeIntrinsics(120.,120.,64.,64.),
        128,128,max_cameras=2,
    )
    assert chosen == (1,0)
    # A different insertion order must not favor the first frame.
    reordered = choose_private_pitched_plane_cameras(
        plane,tuple(reversed(poses)),
        PinholeIntrinsics(120.,120.,64.,64.),
        128,128,max_cameras=2,
    )
    assert reordered == (0,1)


def test_any_additional_visible_roof_coverage_beats_projected_density():
    """A sharper-looking partial view cannot replace a whole-roof source."""
    plane = _facet(-.5,.5)
    poses = (_sampling_camera_pose(2.2,5.),_sampling_camera_pose(0.,9.))
    chosen = choose_private_pitched_plane_cameras(
        plane,poses,PinholeIntrinsics(120.,120.,64.,64.),
        128,128,max_cameras=2,
    )
    assert chosen[0] == 1
    assert set(chosen) == {0,1}


def test_primary_density_does_not_replace_baseline_for_secondary_camera():
    """After a fully covering primary, preserve a different perspective."""
    plane = _facet(-.5,.5)
    poses = (_sampling_camera_pose(0.,5.),
             _sampling_camera_pose(.05,5.),
             _sampling_camera_pose(2.,6.))
    chosen = choose_private_pitched_plane_cameras(
        plane,poses,PinholeIntrinsics(60.,60.,64.,64.),
        128,128,max_cameras=2,
    )
    assert chosen == (0,2)


def test_real_3d_edge_landmarks_select_sources_missed_by_coarse_25_grid():
    """Two narrow real support islands must survive an empty 25x25 sample.

    Geometry is purely synthetic; the 37 m wide pitched candidate has
    dense 3D inliers only at both lateral edges. Its supported radius
    is LESS than the 0.73 m gap to the nearest 25x25 grid-center.
    Neither strip should be lost just because the sample grid misses it.
    """
    plane = _facet(-18.5,18.5)
    yy = np.linspace(-.96,.96,500)
    xy = np.asarray(
        [(x,y) for x in (-18.49,18.49) for y in yy],
        dtype=np.float64,
    )
    plane = replace(
        plane,
        landmark_indices_private=np.arange(len(xy),dtype=np.int32),
        inlier_xy_private_m=xy,
    )
    radius_m = min(
        1.5, max(.35, 2.4*np.sqrt(plane.footprint_area_m2/len(xy))),
    )
    nearest_grid_center_m = 18.49-17.76
    assert radius_m < nearest_grid_center_m
    r = np.diag((1.,-1.,-1.))
    centers = ((-18.5,0.,10.),(18.5,0.,10.))
    poses = tuple(np.column_stack(
        (r,-r @ np.asarray(center,dtype=np.float64))
    ) for center in centers)
    selected = choose_private_pitched_plane_cameras(
        plane,poses,PinholeIntrinsics(60.,60.,64.,64.),
        128,128,max_cameras=2,
    )
    assert set(selected) == {0,1}
    assert len(selected) == 2


def test_spatial_3d_anchor_selection_has_bounded_cost(monkeypatch):
    """Only at most 64 extra real landmarks enter 25x25 selection."""
    from mcm_solarcheck.services import rgb_private_multi_plane_preview as mod
    plane = _facet(-18.5,18.5)
    yy = np.linspace(-.96,.96,500)
    xy = np.asarray([(x,y) for x in (-18.49,18.49) for y in yy])
    plane = replace(
        plane, landmark_indices_private=np.arange(len(xy)),
        inlier_xy_private_m=xy,
    )
    original = mod._private_candidate_supported_ray_hits
    checked = []

    def count_check(candidate, points, **kwargs):
        checked.append(len(points))
        return original(candidate, points, **kwargs)

    monkeypatch.setattr(mod, "_private_candidate_supported_ray_hits",count_check)
    r = np.diag((1.,-1.,-1.))
    poses = tuple(np.column_stack((r,-r @ np.array((x,0.,10.))))
                  for x in (-18.5,18.5))
    chosen = mod.choose_private_pitched_plane_cameras(
        plane,poses,PinholeIntrinsics(60.,60.,64.,64.),128,128,
    )
    assert set(chosen) == {0,1}
    assert checked and max(checked) <= 625


def test_underface_camera_does_not_win_roof_source_selection():
    """Upside-looking pixels are not evidence for an upward-facing roof."""
    plane = _facet(-.5,.5)
    r_above = np.diag((1.,-1.,-1.))
    camera_above = lambda x: np.column_stack((
        r_above, -r_above @ np.array((x,0.,5.)),
    ))
    r_below = np.eye(3)
    below = np.column_stack((r_below,np.zeros(3)))
    # The underface camera has a geometrically valid positive pixel depth
    # and sees all sampled points; old selection incorrectly preferred it.
    k = PinholeIntrinsics(60.,60.,64.,64.)
    with pytest.raises(ValueError,match="fewer than two"):
        choose_private_pitched_plane_cameras(
            plane,(below,camera_above(0.)),k,128,128,
        )
    chosen = choose_private_pitched_plane_cameras(
        plane,(below,camera_above(0.),camera_above(.4)),k,128,128,
    )
    assert set(chosen) == {1,2}
    assert 0 not in chosen
