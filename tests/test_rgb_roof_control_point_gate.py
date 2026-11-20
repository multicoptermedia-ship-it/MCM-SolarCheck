"""Synthetic regression for independently checked tilted RGB plane previews.

The test uses purely generated camera/roof/imagery. It does NOT certify real
Hummintech3 geometry and uploads no project/customer coordinates.
"""
from pathlib import Path

import numpy as np
import pytest

from mcm_solarcheck.domain.models import ImageFrame, Pose
from mcm_solarcheck.services.module_camera_calibration_gate import VerifiedCameraGeometry
from mcm_solarcheck.services.module_plane_basis import basis_from_surveyed_plane
from mcm_solarcheck.services.module_plane_projection import (
    CameraExtrinsicsENU, PinholeIntrinsics, SurveyedPlane3D,
)
from mcm_solarcheck.services.module_plane_rectification import ModuleSurfaceGrid
from mcm_solarcheck.services.rgb_surface_tile_mosaic import RGBMosaicSource
from mcm_solarcheck.services.rgb_surface_tiles import plan_rgb_surface_tiles
from mcm_solarcheck.services.rgb_roof_control_point_gate import (
    RGBRoofHeldOutControl, check_held_out_rgb_roof_controls,
    run_controlled_rgb_roof_pilot,
)
from mcm_solarcheck.services.rgb_surface_pilot_run import RGBSurfacePilotCancelled


def _inputs():
    # Actual mathematical 30-degree plane, NOT an assumed inclination of a real PV roof.
    a = np.deg2rad(30.)
    normal = (0., float(np.sin(a)), float(np.cos(a)))
    plane = SurveyedPlane3D((0., 0., 0.), normal)
    basis = basis_from_surveyed_plane(plane)
    cam_z = -np.asarray(normal)
    cam_x = np.array((1., 0., 0.))
    cam_y = np.cross(cam_z, cam_x)
    rot = np.column_stack((cam_x, cam_y, cam_z))
    center = np.asarray(normal) * 4.
    intrinsics = PinholeIntrinsics(60., 60., 32., 32.)
    sources, controls = [], []
    for i, east_offset in enumerate((0., .15)):
        frame_id = f"synthetic-{i}"
        current_center = center + np.array((east_offset, 0., 0.))
        geometry = VerifiedCameraGeometry(
            intrinsics,
            CameraExtrinsicsENU(
                tuple(current_center),
                tuple(tuple(float(x) for x in row) for row in rot),
            ),
            64, 64, "independent synthetic camera", "synthetic ENU axes",
            "independently surveyed synthetic plane", True, True,
        )
        frame = ImageFrame(
            frame_id, Path("never-open.jpg"), width=64, height=64,
            camera_pose=Pose(0, -90, 0),
        )
        sources.append(RGBMosaicSource(
            frame, np.full((64, 64, 3), 90 + i * 5, np.uint8), geometry,
        ))
        for j, (u, v) in enumerate(((-.6, -.6), (-.6, .6), (.6, -.6), (.6, .6))):
            world = (
                np.asarray(basis.origin_enu_m) +
                u * np.asarray(basis.axis_u_enu) +
                v * np.asarray(basis.axis_v_enu)
            )
            camera = (world - current_center) @ rot
            px = 60. * camera[0] / camera[2] + 32.
            py = 60. * camera[1] / camera[2] + 32.
            controls.append(RGBRoofHeldOutControl(
                frame_id, f"check-{j}", (float(px), float(py)),
                tuple(float(x) for x in world),
            ))
    grid = ModuleSurfaceGrid(-1., -1., .05, 40, 40)
    return plan_rgb_surface_tiles(grid, tile_side_px=32), tuple(sources), plane, tuple(controls)


def _gate(sources, plane, controls, **kwargs):
    return check_held_out_rgb_roof_controls(
        sources, plane, controls,
        allowed_surface_error_m=.1,
        control_survey_provenance="independent synthetic test measurements",
        **kwargs,
    )


def test_tilted_multiview_geometry_with_independent_controls_runs_in_memory():
    plan, sources, plane, controls = _inputs()
    before = [s.undistorted_bgr.copy() for s in sources]
    result = run_controlled_rgb_roof_pilot(
        plan, sources, plane, controls,
        allowed_surface_error_m=.1,
        control_survey_provenance="independent synthetic test measurements",
    )
    audit = result.control_audit
    assert audit.checked_source_count == 2
    assert audit.checked_control_count == 8
    assert audit.maximum_surface_error_m < 1e-10
    assert audit.p95_surface_error_m < 1e-10
    assert audit.control_residuals_within_tolerance
    assert not audit.survey_provenance_independently_verified
    assert not audit.orthophoto_verified
    assert not result.orthophoto_verified
    assert not result.georeferencing_verified
    assert result.preview.processed_tile_count == 4
    assert result.preview.audit.covered_pixels > 0
    assert not result.preview.orthophoto_verified
    for src, old in zip(sources, before):
        np.testing.assert_array_equal(src.undistorted_bgr, old)


def test_shifted_control_rejected_before_any_rgb_tile_is_processed():
    plan, sources, plane, controls = _inputs()
    wrong = list(controls)
    c = wrong[0]
    wrong[0] = RGBRoofHeldOutControl(
        c.frame_id, c.control_id,
        (c.undistorted_pixel_xy[0] + 10., c.undistorted_pixel_xy[1]),
        c.surveyed_point_enu_m,
    )
    progress = []
    with pytest.raises(ValueError, match="residual exceeds"):
        run_controlled_rgb_roof_pilot(
            plan, sources, plane, tuple(wrong),
            allowed_surface_error_m=.1,
            control_survey_provenance="synthetic independent controls",
            on_progress=lambda *args: progress.append(args),
        )
    assert progress == []


def test_controls_cannot_be_sparse_collinear_or_missing_for_one_source():
    _, sources, plane, controls = _inputs()
    with pytest.raises(ValueError, match="insufficient independent controls"):
        _gate(sources, plane, controls[:7])
    with pytest.raises(ValueError, match="distributed"):
        sparse = tuple(
            RGBRoofHeldOutControl(c.frame_id, c.control_id,
                                  c.undistorted_pixel_xy, (0., 0., 0.))
            for c in controls
        )
        _gate(sources, plane, sparse)
    with pytest.raises(ValueError, match="duplicate"):
        _gate(sources, plane, controls + (controls[0],))


def test_missing_calibration_and_unprovenanced_survey_fail_closed():
    _, sources, plane, controls = _inputs()
    with pytest.raises(ValueError, match="provenance"):
        check_held_out_rgb_roof_controls(
            sources, plane, controls,
            allowed_surface_error_m=.1, control_survey_provenance="",
        )
    src = sources[0]
    g = src.geometry
    invalid = VerifiedCameraGeometry(
        g.intrinsics, g.extrinsics, 64, 64, "a", "b", "c", False, True,
    )
    wrong = (RGBMosaicSource(src.frame, src.undistorted_bgr, invalid), sources[1])
    with pytest.raises(ValueError, match="lens correction"):
        _gate(wrong, plane, controls)


def test_cancellation_prevents_pilot_run():
    plan, sources, plane, controls = _inputs()
    with pytest.raises(RGBSurfacePilotCancelled):
        run_controlled_rgb_roof_pilot(
            plan, sources, plane, controls,
            allowed_surface_error_m=.1,
            control_survey_provenance="synthetic independent controls",
            should_cancel=lambda: True,
        )
