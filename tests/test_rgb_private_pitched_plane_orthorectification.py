"""Synthetic pitched RGB orthorectification on actual private 3D plane points.

No original DJI photos, real lens calibration, survey control or roof
certification. Both cameras image the same analytically generated slope.
"""
from dataclasses import replace
import json

import numpy as np
import pytest

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_private_pitched_plane_candidates import (
    PrivateRGBPitchedPlaneCandidate, PrivateRGBPitchedPlaneCandidates,
)
from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
    render_private_pitched_rgb_orthopatch,
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


def _plane():
    n = np.array((-.2, 0., 1.), dtype=np.float64)
    n /= np.linalg.norm(n)
    # z(x,y) = 1 + .2x, i.e. -0.2x + z -1 == 0.
    return PrivateRGBPitchedPlaneCandidate(
        n, -1./np.sqrt(1.04),
        np.arange(32, dtype=np.int32),
        np.array([[-2.,-2.],[2.,-2.],[2.,2.],[-2.,2.]]),
        float(np.degrees(np.arctan(.2))), 4, .01, 16.,
    )


def _source(camera_x, k):
    # Proper R flips north/up: looking DOWN from ENU altitude 5 m.
    r = np.diag((1.,-1.,-1.))
    center = np.array((camera_x,0.,5.))
    pose = np.column_stack((r, -r @ center))
    yy, xx = np.indices((320,320), dtype=np.float64)
    rx = (xx-k.cx)/k.fx
    ry = -(yy-k.cy)/k.fy
    # Intersect each camera ray with z = 1 + .2*x.
    t = (4. - .2*camera_x) / (1. + .2*rx)
    world_x = camera_x + rx*t
    world_y = ry*t
    rgb = np.stack((
        np.clip(128 + 20*world_x, 0, 255),
        np.clip(128 + 20*world_y, 0, 255),
        np.full_like(world_x, 80),
    ), axis=-1).round().astype(np.uint8)
    return rgb, pose


def test_two_real_camera_rays_inverse_project_to_same_pitched_world_rgb():
    k = PinholeIntrinsics(120.,120.,160.,160.)
    sources = [_source(x,k) for x in (0.,.4)]
    original = [image.copy() for image,_ in sources]
    result = render_private_pitched_rgb_orthopatch(
        _plane(), tuple(i for i,_ in sources),
        tuple(p for _,p in sources), k, meters_per_pixel=.05,
    )
    assert result.rgb_private.shape == (80,80,3)
    assert result.planar_pixel_count >= 5900
    assert result.valid_pixel_count == result.planar_pixel_count
    assert result.multi_camera_pixel_count == result.planar_pixel_count
    rr, cc = np.indices(result.valid_mask_private.shape)
    east = -2. + (cc + .5)*.05
    north = 2. - (rr + .5)*.05
    expected = np.stack((
        128 + 20*east,
        128 + 20*north,
        np.full_like(east,80.),
    ), axis=-1)
    error = np.abs(
        result.rgb_private.astype(np.float64) - expected
    )
    assert float(np.max(error[result.valid_mask_private])) <= 2.5
    assert not result.rgb_private.flags.writeable
    assert not result.valid_mask_private.flags.writeable
    assert all(np.array_equal(original[i], sources[i][0]) for i in range(2))
    safe = result.privacy_safe_summary()
    assert safe["multi_camera_coverage_fraction"] == 1.
    assert safe["roof_geometry_verified"] is False
    assert safe["orthophoto_verified"] is False
    assert safe["independent_survey_verified"] is False
    for forbidden in ("rgb_private","top_left_xy", "normal_enu",
                      "offset_enu", "landmark_indices", "DJI_", "GPS"):
        assert forbidden not in json.dumps(safe)


def test_below_plane_or_out_of_view_cannot_fabricate_pixel_coverage():
    k = PinholeIntrinsics(120.,120.,160.,160.)
    source, pose = _source(0., k)
    # The camera looks downward from altitude 0 and the plane is ABOVE it.
    behind = pose.copy()
    behind[:,3] = np.array((0.,0.,0.))
    result = render_private_pitched_rgb_orthopatch(
        _plane(), (source,), (behind,), k,
    )
    assert result.valid_pixel_count == 0
    assert result.multi_camera_pixel_count == 0
    assert not np.any(result.rgb_private)
    assert not np.any(result.valid_mask_private)
    assert result.privacy_safe_summary()["orthophoto_verified"] is False


def test_resource_and_pose_validation_are_fail_closed():
    k = PinholeIntrinsics(120.,120.,160.,160.)
    source, pose = _source(0., k)
    with pytest.raises(ValueError, match="resolution exceeds"):
        render_private_pitched_rgb_orthopatch(
            _plane(), (source,), (pose,), k, meters_per_pixel=.01,
            max_side=64,
        )
    bad = pose.copy()
    bad[0,0] = 1.4
    with pytest.raises(ValueError, match="proper final fitted"):
        render_private_pitched_rgb_orthopatch(
            _plane(), (source,), (bad,), k,
        )
    with pytest.raises(ValueError, match="undistorted RGB"):
        render_private_pitched_rgb_orthopatch(
            _plane(), (source[:,:,0],), (pose,), k,
        )
    with pytest.raises(RuntimeError, match="cancelled"):
        render_private_pitched_rgb_orthopatch(
            _plane(), (source,), (pose,), k,
            should_cancel=lambda: True,
        )


def test_existing_rtk_ba_candidate_can_render_in_memory_with_indexed_cameras():
    k = PinholeIntrinsics(120.,120.,160.,160.)
    sources = [_source(x,k) for x in (0., .4)]
    good_pixel = RGBPerCameraReprojectionAudit(
        12,32,384,32,12,1.,1.,1.,
    )
    good_parallax = RGBMultiviewParallaxAudit(
        12,32,384,.25,.75,32,0,2.,3.,
    )
    poses = tuple(
        sources[i][1] if i < 2 else sources[1][1]
        for i in range(12)
    )
    candidate = PrivateRGBRTKWindowedBA(
        tuple(f"synthetic-{i}" for i in range(12)),
        poses, np.zeros((32,3)), 1.,.5,.1,.1,.15,
        10,2,12,3,20.,10.,
        camera_reprojection_audit=good_pixel,
        multiview_parallax_audit=good_parallax,
        pitched_plane_candidates=PrivateRGBPitchedPlaneCandidates(
            (_plane(),),32,
        ),
    )
    patch = candidate.render_private_pitched_plane_preview(
        0, tuple(im for im,_ in sources), (0,1), k,
    )
    assert patch.valid_pixel_count == patch.planar_pixel_count
    assert patch.privacy_safe_summary()["orthophoto_verified"] is False
    with pytest.raises(ValueError, match="valid fitted"):
        candidate.render_private_pitched_plane_preview(
            1, tuple(im for im,_ in sources), (0,1), k,
        )
    with pytest.raises(ValueError, match="valid fitted"):
        replace(candidate, camera_reprojection_audit=None
                ).render_private_pitched_plane_preview(
            0, tuple(im for im,_ in sources), (0,1), k,
        )



def test_other_pitched_plane_blocks_one_camera_not_unobstructed_camera():
    """Two fitted facets: do not average source view behind a nearer face."""
    k = PinholeIntrinsics(60.,60.,64.,64.)
    n = np.array((-.2,0.,1.), dtype=np.float64)
    n /= np.linalg.norm(n)
    target = PrivateRGBPitchedPlaneCandidate(
        n, -n[2], np.arange(32,dtype=np.int32),
        np.array([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]]),
        11.3,4,.01,1.,
    )
    blocker = PrivateRGBPitchedPlaneCandidate(
        n, -3*n[2], np.arange(32,dtype=np.int32),
        np.array([[-.7,-.7],[.7,-.7],[.7,.7],[-.7,.7]]),
        11.3,4,.01,1.96,
    )
    r = np.diag((1.,-1.,-1.))
    centers = (np.array((0.,0.,5.)),np.array((3.,0.,5.)))
    poses = tuple(np.column_stack((r,-r @ center)) for center in centers)
    images = (np.full((128,128,3),(255,0,0),dtype=np.uint8),
              np.full((128,128,3),(0,0,255),dtype=np.uint8))
    plain = render_private_pitched_rgb_orthopatch(
        target,images,poses,k,meters_per_pixel=.05,
    )
    clipped = render_private_pitched_rgb_orthopatch(
        target,images,poses,k,meters_per_pixel=.05,
        occluder_planes=(blocker,),
    )
    mid = (10,10)
    assert plain.valid_mask_private[mid]
    assert clipped.valid_mask_private[mid]
    np.testing.assert_array_equal(plain.rgb_private[mid],(128,0,128))
    np.testing.assert_array_equal(clipped.rgb_private[mid],(0,0,255))
    assert clipped.candidate_occluded_source_pixels > 0
    assert clipped.privacy_safe_summary()["candidate_occluded_source_pixels"] > 0
    assert clipped.privacy_safe_summary()["orthophoto_verified"] is False
    assert not clipped.rgb_private.flags.writeable


def test_other_pitched_plane_can_make_hidden_pixels_transparent():
    k = PinholeIntrinsics(60.,60.,64.,64.)
    n = np.array((-.2,0.,1.), dtype=np.float64)
    n /= np.linalg.norm(n)
    target = PrivateRGBPitchedPlaneCandidate(
        n,-n[2],np.arange(32),np.array(
            [[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]]),
        11.3,4,.01,1.,
    )
    blocker = PrivateRGBPitchedPlaneCandidate(
        n,-3*n[2],np.arange(32),np.array(
            [[-2.,-2.],[2.,-2.],[2.,2.],[-2.,2.]]),
        11.3,4,.01,16.,
    )
    r = np.diag((1.,-1.,-1.))
    center = np.array((0.,0.,5.))
    pose = np.column_stack((r,-r @ center))
    image = np.full((128,128,3),120,dtype=np.uint8)
    clipped = render_private_pitched_rgb_orthopatch(
        target,(image,),(pose,),k,meters_per_pixel=.05,
        occluder_planes=(blocker,),
    )
    assert clipped.candidate_occluded_source_pixels > 0
    assert not clipped.valid_mask_private.any()
    assert not clipped.rgb_private.any()
    assert clipped.privacy_safe_summary()["orthophoto_verified"] is False
    unfiltered = render_private_pitched_rgb_orthopatch(
        target,(image,),(pose,),k,meters_per_pixel=.05,
    )
    assert unfiltered.valid_pixel_count > 0


def test_priority_fusion_keeps_one_camera_color_and_only_falls_back_at_holes():
    """Overlapping red/blue sources must never create purple PV ghosts."""
    k = PinholeIntrinsics(200.,200.,64.,64.)
    r = np.diag((1.,-1.,-1.))
    centers = (np.array((-1.2,0.,5.)),np.array((1.2,0.,5.)))
    poses = tuple(np.column_stack((r,-r @ center)) for center in centers)
    images = (
        np.full((128,128,3),(255,0,0),dtype=np.uint8),
        np.full((128,128,3),(0,0,255),dtype=np.uint8),
    )
    preview = render_private_pitched_rgb_orthopatch(
        _plane(),images,poses,k,meters_per_pixel=.05,
        source_fusion="priority",
    )
    assert preview.source_fusion == "priority"
    assert preview.multi_camera_pixel_count > 0
    assert 0 < preview.secondary_source_pixel_count < preview.valid_pixel_count
    assert preview.valid_mask_private[40, 10]
    assert preview.valid_mask_private[40, 70]
    np.testing.assert_array_equal(preview.rgb_private[40,10],(255,0,0))
    np.testing.assert_array_equal(preview.rgb_private[40,70],(0,0,255))
    # The overlap is guaranteed to be an existing camera sample, not mean.
    assert np.all(preview.rgb_private[preview.valid_mask_private,1] == 0)
    colors = set(map(tuple,preview.rgb_private[preview.valid_mask_private]))
    assert colors == {(255,0,0),(0,0,255)}
    safe = preview.privacy_safe_summary()
    assert safe["source_fusion"] == "priority"
    assert safe["secondary_source_pixel_count"] > 0
    assert safe["orthophoto_verified"] is False
    assert not preview.rgb_private.flags.writeable
    for secret in ("top_left_xy","rgb_private","GPS","DJI_"):
        assert secret not in json.dumps(safe)


def test_priority_fusion_excludes_candidate_occluded_primary_before_fallback():
    """Candidate visibility beats source preference even with constant RGB."""
    k = PinholeIntrinsics(60.,60.,64.,64.)
    n = np.array((-.2,0.,1.),dtype=np.float64)
    n /= np.linalg.norm(n)
    target = PrivateRGBPitchedPlaneCandidate(
        n,-n[2],np.arange(32,dtype=np.int32),
        np.array([[-.5,-.5],[.5,-.5],[.5,.5],[-.5,.5]]),
        11.3,4,.01,1.,
    )
    occluder = PrivateRGBPitchedPlaneCandidate(
        n,-3*n[2],np.arange(32,dtype=np.int32),
        np.array([[-.7,-.7],[.7,-.7],[.7,.7],[-.7,.7]]),
        11.3,4,.01,1.96,
    )
    r = np.diag((1.,-1.,-1.))
    centers = (np.array((0.,0.,5.)),np.array((3.,0.,5.)))
    poses = tuple(np.column_stack((r,-r @ center)) for center in centers)
    images = (
        np.full((128,128,3),(255,0,0),dtype=np.uint8),
        np.full((128,128,3),(0,0,255),dtype=np.uint8),
    )
    preview = render_private_pitched_rgb_orthopatch(
        target, images, poses, k, meters_per_pixel=.05,
        occluder_planes=(occluder,), source_fusion="priority",
    )
    assert preview.valid_mask_private[10,10]
    np.testing.assert_array_equal(preview.rgb_private[10,10],(0,0,255))
    assert preview.candidate_occluded_source_pixels > 0
    assert preview.secondary_source_pixel_count > 0
    assert preview.privacy_safe_summary()["orthophoto_verified"] is False


def test_bad_source_fusion_mode_is_rejected_without_rendering():
    k = PinholeIntrinsics(120.,120.,160.,160.)
    source,pose = _source(0.,k)
    with pytest.raises(ValueError,match="bounded private pitched"):
        render_private_pitched_rgb_orthopatch(
            _plane(), (source,), (pose,), k,
            source_fusion="radiometric_quality_verified",
        )



def test_priority_overlap_aligns_small_rgb_exposure_jump_without_blending():
    """A real 3D-overlap shift adjusts ONLY later camera's fallback pixels."""
    k = PinholeIntrinsics(200.,200.,64.,64.)
    r = np.diag((1.,-1.,-1.))
    centers = (np.array((-.9,0.,5.)),np.array((.9,0.,5.)))
    poses = tuple(np.column_stack((r,-r @ center)) for center in centers)
    base = np.array((110,120,130), dtype=np.uint8)
    offset = np.array((12,14,16), dtype=np.uint8)
    images = (
        np.broadcast_to(base,(128,128,3)).copy(),
        np.broadcast_to(base+offset,(128,128,3)).copy(),
    )
    raw = render_private_pitched_rgb_orthopatch(
        _plane(),images,poses,k,meters_per_pixel=.05,
        source_fusion="priority",
    )
    corrected = render_private_pitched_rgb_orthopatch(
        _plane(),images,poses,k,meters_per_pixel=.05,
        source_fusion="priority_overlap",
    )
    # The first camera's pixels remain byte-identical; no RGB blend.
    np.testing.assert_array_equal(corrected.rgb_private[40, 15],base)
    np.testing.assert_array_equal(raw.rgb_private[40, 75],base+offset)
    np.testing.assert_array_equal(corrected.rgb_private[40, 75],base)
    assert corrected.valid_pixel_count == raw.valid_pixel_count
    assert corrected.multi_camera_pixel_count > 128
    assert corrected.radiometric_corrected_source_count == 1
    assert corrected.radiometric_overlap_support_pixels >= 128
    assert corrected.source_fusion == "priority_overlap"
    assert not corrected.rgb_private.flags.writeable
    assert not corrected.valid_mask_private.flags.writeable
    np.testing.assert_array_equal(images[1][0,0],base+offset)
    safe = corrected.privacy_safe_summary()
    assert safe["radiometric_corrected_source_count"] == 1
    assert safe["orthophoto_verified"] is False
    for secret in ("rgb_private","top_left_xy","GPS","DJI_"):
        assert secret not in json.dumps(safe)


def test_priority_overlap_does_not_invent_alignment_without_overlap():
    k = PinholeIntrinsics(200.,200.,64.,64.)
    r = np.diag((1.,-1.,-1.))
    centers = (np.array((-1.35,0.,5.)),np.array((1.35,0.,5.)))
    poses = tuple(np.column_stack((r,-r @ center)) for center in centers)
    colors = ((110,120,130),(122,134,146))
    images = tuple(np.full((128,128,3),color,dtype=np.uint8)
                   for color in colors)
    patch = render_private_pitched_rgb_orthopatch(
        _plane(),images,poses,k,meters_per_pixel=.05,
        source_fusion="priority_overlap",
    )
    assert patch.secondary_source_pixel_count > 0
    assert patch.radiometric_corrected_source_count == 0
    assert patch.radiometric_overlap_support_pixels == 0
    np.testing.assert_array_equal(patch.rgb_private[40, 5],colors[0])
    np.testing.assert_array_equal(patch.rgb_private[40, 75],colors[1])
    assert patch.privacy_safe_summary()["orthophoto_verified"] is False


def test_overlap_color_estimation_rejects_inconsistent_or_saturated_samples():
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _private_robust_overlap_color_offset,
    )
    h,w = 40,60
    reference = np.full((h*w,3),125,dtype=np.uint8)
    alternating = np.full((h,w,3),125,dtype=np.uint8)
    alternating[::2,:,:] = 190
    ref_mask = np.zeros((h,w),dtype=bool)
    ref_mask[:,:50] = True
    source_mask = np.ones(h*w,dtype=bool)
    fallback = ~ref_mask
    ref_mask = ref_mask.ravel()
    assert _private_robust_overlap_color_offset(
        reference, alternating.reshape(-1,3),
        ref_mask, source_mask, fallback.ravel(), h,w
    ) is None
    # Clearly different scene, beyond the tight correction clamp.
    too_far = np.full((h*w,3),175,dtype=np.uint8)
    assert _private_robust_overlap_color_offset(
        reference, too_far, ref_mask, source_mask, fallback.ravel(), h,w
    ) is None
    black = np.zeros((h*w,3),dtype=np.uint8)
    assert _private_robust_overlap_color_offset(
        black, reference, ref_mask, source_mask, fallback.ravel(), h,w
    ) is None



def test_rgb_offset_samples_actual_seam_not_distant_illumination():
    """The same roof facet may have different shifts far from a source swap."""
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _private_robust_overlap_color_offset,
    )
    height, width = 40,60
    reference = np.full((height,width,3), (110,120,130),dtype=np.uint8)
    second = reference.copy()
    second[:,:42,:] += np.array((2,2,2),dtype=np.uint8)
    second[:,42:,:] += np.array((12,10,8),dtype=np.uint8)
    reference_valid = np.zeros((height,width),dtype=bool)
    reference_valid[:,:50] = True
    fallback = ~reference_valid
    estimate = _private_robust_overlap_color_offset(
        reference.reshape(-1,3), second.reshape(-1,3),
        reference_valid.ravel(), np.ones(height*width,dtype=bool),
        fallback.ravel(), height, width,
    )
    assert estimate is not None
    shift, samples = estimate
    # Whole-image median would be (-2,-2,-2): wrong AT THE SEAM.
    np.testing.assert_array_equal(shift,(-12,-10,-8))
    assert samples >= 128


def test_rgb_offset_does_not_use_remote_overlap_without_adjacent_support():
    """No accidental correction from a separate patch far from the seam."""
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _private_robust_overlap_color_offset,
    )
    height,width = 40,60
    rgb_ref = np.full((height*width,3),120,dtype=np.uint8)
    rgb_later = np.full((height*width,3),135,dtype=np.uint8)
    reference_valid = np.zeros((height,width),dtype=bool)
    reference_valid[:, :15] = True
    fallback = np.zeros((height,width),dtype=bool)
    fallback[:, 45:] = True
    candidate_valid = (reference_valid | fallback).ravel()
    assert _private_robust_overlap_color_offset(
        rgb_ref, rgb_later, reference_valid.ravel(),candidate_valid,
        fallback.ravel(),height,width,
    ) is None


def test_rgb_offset_fails_closed_on_overlapping_source_seam_masks():
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _private_robust_overlap_color_offset,
    )
    height,width = 40,60
    rgb = np.full((height*width,3),120,dtype=np.uint8)
    mask = np.ones(height*width,dtype=bool)
    with pytest.raises(ValueError,match="disjoint RGB source-seam"):
        _private_robust_overlap_color_offset(
            rgb,rgb,mask,mask,mask,height,width,
        )



def test_source_boundary_color_jump_audit_only_counts_actual_camera_switches():
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _private_label_transition_rgb_jump,
    )
    rgb = np.full((5,6,3),(100,120,130),dtype=np.uint8)
    owner = np.zeros((5,6),dtype=np.uint8)
    owner[:,3:] = 1
    mask = np.ones((5,6),dtype=bool)
    rgb[:,3:] = (115,120,130)
    count,p95 = _private_label_transition_rgb_jump(rgb,owner,mask)
    assert count == 5 and p95 == 15.
    # Uncovered pixels must not be treated as false camera seams.
    mask[:,2:4] = False
    assert _private_label_transition_rgb_jump(rgb,owner,mask) == (0,None)
    assert _private_label_transition_rgb_jump(
        rgb,np.zeros_like(owner),np.ones_like(mask)
    ) == (0,None)


def test_real_priority_rendering_exposes_seam_count_but_not_source_map():
    k = PinholeIntrinsics(200.,200.,64.,64.)
    r = np.diag((1.,-1.,-1.))
    centers = (np.array((-1.2,0.,5.)),np.array((1.2,0.,5.)))
    poses = tuple(np.column_stack((r,-r @ center)) for center in centers)
    images = (
        np.full((128,128,3),(120,120,120),dtype=np.uint8),
        np.full((128,128,3),(145,120,120),dtype=np.uint8),
    )
    preview = render_private_pitched_rgb_orthopatch(
        _plane(),images,poses,k,meters_per_pixel=.05,
        source_fusion="priority",
    )
    assert preview.candidate_camera_seam_boundary_pairs > 0
    assert preview.candidate_camera_seam_rgb_jump_p95 == 25.
    summary = preview.privacy_safe_summary()
    assert summary["candidate_camera_seam_boundary_pairs"] > 0
    assert summary["candidate_camera_seam_rgb_jump_p95"] == 25.
    assert summary["orthophoto_verified"] is False
    for secret in ("source_map", "source_index", "top_left_xy", "GPS", "DJI_"):
        assert secret not in json.dumps(summary)


def test_sparse_supported_3d_landmarks_leave_convex_hull_gap_transparent():
    """The camera sees the gap, but post-BA point support does not."""
    k = PinholeIntrinsics(120.,120.,160.,160.)
    image, pose = _source(0.,k)
    x = np.r_[np.linspace(-1.95,-1.65,4),
              np.linspace(1.65,1.95,4)]
    y = np.linspace(-1.85,1.85,12)
    xx, yy = np.meshgrid(x,y)
    points = np.column_stack((xx.ravel(),yy.ravel()))
    point_supported = replace(
        _plane(),
        landmark_indices_private=np.arange(len(points),dtype=np.int32),
        inlier_xy_private_m=points,
    )
    full = render_private_pitched_rgb_orthopatch(
        _plane(),(image,),(pose,),k,meters_per_pixel=.05,
    )
    patch = render_private_pitched_rgb_orthopatch(
        point_supported,(image,),(pose,),k,meters_per_pixel=.05,
    )
    assert full.valid_mask_private[40,40]
    assert not patch.valid_mask_private[40,40]  # central convex-hull void
    assert not np.any(patch.rgb_private[40,40])
    assert patch.valid_mask_private[40,7]
    assert patch.valid_mask_private[40,73]
    assert patch.unsupported_convex_hull_pixels > 0
    assert patch.valid_pixel_count < full.valid_pixel_count
    assert not patch.valid_mask_private.flags.writeable
    assert patch.privacy_safe_summary()["orthophoto_verified"] is False
    for forbidden in ("inlier_xy", "landmark_indices", "top_left_xy", "GPS"):
        assert forbidden not in json.dumps(patch.privacy_safe_summary())


def test_invalid_3d_landmark_support_fails_closed_without_rgb_fabrication():
    k = PinholeIntrinsics(120.,120.,160.,160.)
    image,pose = _source(0.,k)
    with pytest.raises(ValueError,match="inlier support"):
        render_private_pitched_rgb_orthopatch(
            replace(_plane(),inlier_xy_private_m=np.array([[0.,np.nan]])),
            (image,),(pose,),k,
        )
    with pytest.raises(ValueError,match="inlier support"):
        render_private_pitched_rgb_orthopatch(
            replace(_plane(),inlier_xy_private_m=np.full((32,2),200.)),
            (image,),(pose,),k,
        )



def _synthetic_sparse_upper_occluder():
    """Two 3D-supported stripes, with a true unmeasured convex-hull gap."""
    n = np.array((-.2,0.,1.),dtype=np.float64)
    n /= np.linalg.norm(n)
    support = np.asarray([
        (x,y) for x in (-.6,.6) for y in np.linspace(-.62,.62,64)
    ],dtype=np.float64)
    candidate = PrivateRGBPitchedPlaneCandidate(
        n,-3*n[2],np.arange(len(support),dtype=np.int32),
        np.array([[-.7,-.7],[.7,-.7],[.7,.7],[-.7,.7]]),
        11.3,4,.01,1.96,inlier_xy_private_m=support,
    )
    return candidate


def test_candidate_occlusion_requires_real_landmark_support_not_convex_void():
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _candidate_plane_occlusion_mask,
    )
    upper = _synthetic_sparse_upper_occluder()
    center = np.array((0.,0.,5.))
    target = np.array([[0.,0.,1.],[1.2,0.,1.],[-1.2,0.,1.]])
    eligible = np.ones(3,dtype=bool)
    # Existing convex-only diagnostic candidate treats ALL intersections
    # as occluded. Fitted candidate has a missing 3D strip at x=0.
    legacy = replace(upper,inlier_xy_private_m=None)
    assert _candidate_plane_occlusion_mask(
        target,center,eligible,(legacy,),
    ).tolist() == [True,True,True]
    supported = _candidate_plane_occlusion_mask(
        target,center,eligible,(upper,),
    )
    assert supported.tolist() == [False,True,True]
    assert not _candidate_plane_occlusion_mask(
        target,center,np.zeros(3,dtype=bool),(upper,),
    ).any()


def test_3d_supported_occluder_changes_real_camera_orthoprojection_visibility():
    k = PinholeIntrinsics(120.,120.,160.,160.)
    image,pose = _source(0.,k)
    original = image.copy()
    upper = _synthetic_sparse_upper_occluder()
    actual = render_private_pitched_rgb_orthopatch(
        _plane(),(image,),(pose,),k,meters_per_pixel=.05,
        occluder_planes=(upper,),source_fusion="priority",
    )
    legacy = render_private_pitched_rgb_orthopatch(
        _plane(),(image,),(pose,),k,meters_per_pixel=.05,
        occluder_planes=(replace(upper,inlier_xy_private_m=None),),
        source_fusion="priority",
    )
    assert actual.valid_mask_private[40,40]
    assert not legacy.valid_mask_private[40,40]
    assert 0 < actual.candidate_occluded_source_pixels
    assert actual.candidate_occluded_source_pixels < (
        legacy.candidate_occluded_source_pixels
    )
    assert np.array_equal(image,original)
    assert not actual.rgb_private.flags.writeable
    summary = actual.privacy_safe_summary()
    assert summary["roof_geometry_verified"] is False
    assert summary["orthophoto_verified"] is False
    for forbidden in ("inlier_xy","landmark_indices","top_left_xy","GPS"):
        assert forbidden not in json.dumps(summary)


def test_malformed_occluder_inlier_geometry_is_not_accepted():
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _candidate_plane_occlusion_mask,
    )
    plane = _synthetic_sparse_upper_occluder()
    with pytest.raises(ValueError,match="inlier support"):
        _candidate_plane_occlusion_mask(
            np.array([[0.,0.,1.]]),np.array([0.,0.,5.]),
            np.array([True]),(
                replace(plane,inlier_xy_private_m=np.full((128,2),np.nan)),
            ),
        )


def test_camera_below_pitched_plane_cannot_paint_its_upward_roof_face():
    """RGB camera looking UP can project but must not depict the roof TOP."""
    plane = _plane()
    k = PinholeIntrinsics(120.,120.,160.,160.)
    underside = np.column_stack((np.eye(3),np.zeros(3)))
    top_r = np.diag((1.,-1.,-1.))
    top_center = np.array((0.,0.,5.))
    topside = np.column_stack((top_r,-top_r @ top_center))
    fake_under_rgb = np.full((320,320,3),(0,220,0),dtype=np.uint8)
    actual_top_rgb = np.full((320,320,3),(170,0,0),dtype=np.uint8)
    invisible = render_private_pitched_rgb_orthopatch(
        plane,(fake_under_rgb,),(underside,),k,
        meters_per_pixel=.05,source_fusion="priority",
    )
    assert invisible.valid_pixel_count == 0
    assert not np.any(invisible.rgb_private)
    preview = render_private_pitched_rgb_orthopatch(
        plane,(fake_under_rgb,actual_top_rgb),(underside,topside),k,
        meters_per_pixel=.05,source_fusion="priority",
    )
    assert preview.valid_mask_private[40,40]
    np.testing.assert_array_equal(preview.rgb_private[40,40],(170,0,0))
    assert preview.secondary_source_pixel_count == preview.valid_pixel_count
    assert not preview.rgb_private.flags.writeable
    assert not preview.privacy_safe_summary()["orthophoto_verified"]


def test_extreme_grazing_roof_rays_rejected_without_losing_overhead_pixels():
    from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
        _private_front_surface_visibility,
    )
    n = np.array((0.,0.,1.))
    center = np.array((0.,0.,1.11))
    pts = np.array(((0.,0.,1.), (2.,0.,1.),(-2.,0.,1.)))
    assert _private_front_surface_visibility(n,-1.,center,pts).tolist() == [
        True,False,False,
    ]


def test_slanted_fitted_footprint_exterior_pixel_centers_remain_transparent():
    """Rounded OpenCV hull fills MUST NOT invent RGB outside real hull.

    A diagonal 3D facet edge includes dozens of outside pixel centers if
    fillConvexPoly's vertex-rounded mask is trusted without metric testing.
    No private RGB or ENU edge coordinates leave the in-memory result.
    """
    import cv2

    plane = replace(
        _plane(),
        footprint_xy_private_m=np.array([
            [-2.,-2.],[2.,-2.],[-2.,.83],
        ],dtype=np.float64),
        footprint_area_m2=5.66,
    )
    k = PinholeIntrinsics(120.,120.,160.,160.)
    image,pose = _source(0.,k)
    original_image = image.copy()
    result = render_private_pitched_rgb_orthopatch(
        plane,(image,),(pose,),k,meters_per_pixel=.05,
        source_fusion="priority",
    )
    h,w = result.valid_mask_private.shape
    rows,columns = np.indices((h,w))
    east = -2. + (columns+.5)*.05
    north = .83 - (rows+.5)*.05
    polygon = np.asarray(plane.footprint_xy_private_m,dtype=np.float32)
    geometrically_inside = np.asarray([
        cv2.pointPolygonTest(polygon,(float(x),float(y)),False) >= 0
        for x,y in zip(east.ravel(),north.ravel())
    ]).reshape(h,w)
    # Verify that the old rasterized hull REALLY is over-inclusive here;
    # otherwise the test would not exercise the regression.
    poly = np.column_stack((
        (polygon[:,0]+2.)/.05-.5,
        (.83-polygon[:,1])/.05-.5,
    ))
    old = np.zeros((h,w),dtype=np.uint8)
    cv2.fillConvexPoly(old,np.round(poly).astype(np.int32),1)
    would_fabricate = old.astype(bool) & ~geometrically_inside
    assert np.count_nonzero(would_fabricate) >= 15
    assert not np.any(result.valid_mask_private[would_fabricate])
    assert not np.any(result.rgb_private[would_fabricate])
    assert result.valid_mask_private[40,10]
    assert np.array_equal(image,original_image)
    assert not result.rgb_private.flags.writeable
    assert result.privacy_safe_summary()["orthophoto_verified"] is False
    for forbidden in ("top_left_xy","inlier_xy","GPS","DJI_"):
        assert forbidden not in json.dumps(result.privacy_safe_summary())
