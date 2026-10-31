"""Private multi-plane RGB preview: camera selection and common metric grid.

Vertical development after the BA pitched-plane renderer. All camera indices,
candidate polygons, ENU positions and RGB pixels are STRICTLY RAM ONLY.
A projected sample is not physical visibility or a real roof label. Overlap
is treated conservatively: near-equal-height planes remain ambiguous, never
silently averaged into invented roof detail.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_private_pitched_plane_candidates import (
    PrivateRGBPitchedPlaneCandidate,
)
from mcm_solarcheck.services.rgb_private_pitched_plane_orthorectification import (
    PrivateRGBPitchedPlaneOrthopatch,
    _private_label_transition_rgb_jump,
    _private_candidate_inlier_support,
    _private_candidate_supported_ray_hits,
    _private_front_surface_visibility,
    _candidate_plane_occlusion_mask,
)


def choose_private_pitched_plane_cameras(
    plane: PrivateRGBPitchedPlaneCandidate,
    poses_enu_to_camera: tuple[np.ndarray, ...],
    intrinsics: PinholeIntrinsics,
    image_width: int,
    image_height: int,
    *,
    max_cameras: int = 8,
    min_sample_coverage: float = .20,
    occluder_planes: tuple[PrivateRGBPitchedPlaneCandidate, ...] = (),
    should_cancel=None,
) -> tuple[int, ...]:
    """Select 2..8 strongest visible cameras from fitted BA geometry alone.

    Uses a bounded 25x25 XY sample PLUS at most 64 stratified actual
    3D landmarks on a fitted candidate (not just its convex hull), then
    projects exact plane heights
    with final BA camera poses. ALL geometrically eligible fitted cameras
    are checked against candidate occluders BEFORE opening RGB JPEGs;
    repeat point-distance grids are cached privately per selection call.
    Underside and nearly grazing modeled rays are INVALID in both
    selection and orthorectification. Choose by newly visible target
    support. Where coverage ties, prefer
    stronger geometric projected pixel sampling for the PRIMARY source,
    and camera separation for redundancy. These are NOT measured GSD,
    sharpness or true photometric visibility;
    prefer baseline only as a tie-breaker. This is STILL only a geometric
    visibility hypothesis, not a verified photograph or surveyed roof.
    """
    if should_cancel is not None and should_cancel():
        raise RuntimeError("private multi-plane camera selection cancelled")
    if (not isinstance(plane, PrivateRGBPitchedPlaneCandidate)
            or not isinstance(intrinsics, PinholeIntrinsics)
            or type(poses_enu_to_camera) is not tuple
            or not 2 <= len(poses_enu_to_camera) <= 1000
            or type(image_width) is not int or not 32 <= image_width <= 8000
            or type(image_height) is not int or not 32 <= image_height <= 6000
            or type(max_cameras) is not int or not 2 <= max_cameras <= 8
            or type(min_sample_coverage) not in (int, float)
            or not np.isfinite(min_sample_coverage)
            or not .05 <= min_sample_coverage <= 1.
            or type(occluder_planes) is not tuple
            or len(occluder_planes) > 5
            or any(not isinstance(other, PrivateRGBPitchedPlaneCandidate)
                   for other in occluder_planes)):
        raise ValueError("bounded private plane camera selection required")
    k = np.array((intrinsics.fx, intrinsics.fy,
                  intrinsics.cx, intrinsics.cy), dtype=np.float64)
    n = np.asarray(plane.normal_enu_private, dtype=np.float64)
    hull = np.asarray(plane.footprint_xy_private_m, dtype=np.float64)
    offset = float(plane.signed_offset_enu_private_m)
    if (not np.isfinite(k).all() or np.any(k[:2] <= 0)
            or n.shape != (3,) or not np.isfinite(n).all()
            or not np.isclose(np.linalg.norm(n), 1., atol=1.e-4)
            or n[2] <= .1 or hull.ndim != 2 or hull.shape[1] != 2
            or len(hull) < 3 or not np.isfinite(hull).all()
            or not np.isfinite(offset)):
        raise ValueError("invalid private pitch camera geometry")
    minimum, maximum = hull.min(axis=0), hull.max(axis=0)
    if np.any(maximum - minimum <= 1.e-5):
        raise ValueError("degenerate pitched plane footprint")
    xs = minimum[0] + (np.arange(25)+.5)/25. * (maximum[0]-minimum[0])
    ys = minimum[1] + (np.arange(25)+.5)/25. * (maximum[1]-minimum[1])
    xx, yy = np.meshgrid(xs, ys)
    xy = np.column_stack((xx.ravel(), yy.ravel()))
    # pointPolygonTest is strictly geometric; not a roof semantic classifier.
    interior = np.asarray([
        cv2.pointPolygonTest(np.asarray(hull, np.float32), tuple(map(float, p)),
                             False) >= 0 for p in xy
    ])
    xy = xy[interior]
    # Honor the SAME fitted inlier support as the actual RGB target mask.
    # Otherwise cameras that only see unsupported convex-hull gaps win.
    if plane.inlier_xy_private_m is not None:
        if len(xy):
            supported = _private_candidate_supported_ray_hits(
                plane, xy, should_cancel=should_cancel,
            )
            xy = xy[supported]
        # Even 25x25 may MISS a real, narrow roof edge or detached
        # triangulated landmark island, especially when the point-support
        # radius is smaller than half the grid spacing. Add up to 64
        # deterministic, spatially stratified REAL post-BA inlier anchors.
        # This is still provisional plane support, NOT a roof boundary.
        inliers = _private_candidate_inlier_support(plane)[0]
        buckets = np.clip(
            np.floor((inliers-minimum) / (maximum-minimum) * 8.)
            .astype(np.int32), 0, 7,
        )
        ids = buckets[:, 0] + 8*buckets[:, 1]
        _, representative = np.unique(ids, return_index=True)
        anchor_xy = inliers[np.sort(representative)]
        xy = np.vstack((xy, anchor_xy))
    if len(xy) < 4:
        raise ValueError("insufficient pitched plane area for camera selection")
    z = (-offset - n[0]*xy[:, 0] - n[1]*xy[:, 1]) / n[2]
    points = np.column_stack((xy, z))
    masks = []
    centers = []
    projected_sampling = []
    for i, pose in enumerate(poses_enu_to_camera):
        if should_cancel is not None and i % 16 == 0 and should_cancel():
            raise RuntimeError("private multi-plane camera selection cancelled")
        p = np.asarray(pose, dtype=np.float64)
        if p.shape != (3, 4) or not np.isfinite(p).all():
            raise ValueError("invalid final RGB BA camera pose")
        r, t = p[:, :3], p[:, 3]
        if (not np.allclose(r.T @ r, np.eye(3), atol=1.e-4)
                or not np.isclose(np.linalg.det(r), 1., atol=1.e-4)):
            raise ValueError("invalid final RGB BA camera rotation")
        centers.append(-r.T @ t)
        local = points @ r.T + t
        depth = local[:, 2]
        safe = np.where(depth > 1.e-8, depth, 1.)
        u = k[0]*local[:, 0]/safe + k[2]
        v = k[1]*local[:, 1]/safe + k[3]
        in_image = ((depth > 1.e-8) & np.isfinite(u) & np.isfinite(v)
                    & (u >= 0) & (v >= 0)
                    & (u < image_width-1) & (v < image_height-1))
        # Forward-projecting below-plane or grazing rays is possible, but
        # those cannot reliably sample the UPWARD roof face. Apply the
        # same geometric visibility used by the final RGB renderer.
        if np.any(in_image):
            indices = np.flatnonzero(in_image)
            in_image[indices] = _private_front_surface_visibility(
                n, offset, centers[-1], points[indices],
            )
        masks.append(in_image)
        # For a fitted plane, the pinhole area-Jacobian is
        # fx*fy*|normal · (camera_center - plane_point)|/camera_depth**3.
        # Its square root estimates projected source pixels per plane
        # meter. Use a robust lower quartile, not inferred source-image
        # sharpness or an independently measured ground sampling distance.
        # Only an exact coverage tie may promote this geometric measure.
        if np.any(in_image):
            normal_distance = abs(float(n @ centers[-1]) + offset)
            pixels_per_m = np.sqrt(
                np.clip(k[0]*k[1]*normal_distance
                        / depth[in_image]**3, 0., 1.e12)
            )
            projected_sampling.append(
                float(np.percentile(pixels_per_m, 25))
            )
        else:
            projected_sampling.append(0.)
    valid = [i for i, mask in enumerate(masks)
             if float(np.mean(mask)) >= min_sample_coverage]
    if occluder_planes and valid:
        # Examine ALL up to 1000 already-bounded fitted poses, not the top
        # 32 by raw footprint coverage. A nadir shot can cover the whole
        # footprint yet be totally hidden behind an upper candidate facet;
        # the only useful oblique views might be ranked 33rd or later.
        # Reuse at most five candidate distance grids within this call.
        grid_cache = {}
        visible = []
        for i in valid:
            if should_cancel is not None and should_cancel():
                raise RuntimeError("private multi-plane camera selection cancelled")
            blocked = _candidate_plane_occlusion_mask(
                points, centers[i], masks[i], occluder_planes,
                should_cancel=should_cancel,
                _grid_cache=grid_cache,
            )
            masks[i] &= ~blocked
            if float(np.mean(masks[i])) >= min_sample_coverage:
                visible.append(i)
        valid = visible
    if len(valid) < 2:
        raise ValueError("fewer than two fitted cameras cover pitched RGB plane")
    centers = np.asarray(centers, dtype=np.float64)
    selected: list[int] = []
    covered = np.zeros(len(xy), dtype=bool)
    radius = max(float(np.linalg.norm(maximum-minimum)), 1.)
    # Maximally cover actual visible 3D-supported targets first. For the
    # primary (which actually supplies most RGB pixels) prefer a camera
    # with more projected pixel sampling when coverage is equal. After
    # that, retain genuinely different camera centers for redundancy.
    # No resolution heuristic can override even one additional supported
    # visible sample or force selection of an occluded camera.
    while len(selected) < min(max_cameras, len(valid)):
        def quality(i):
            additional = int(np.count_nonzero(masks[i] & ~covered))
            base = int(np.count_nonzero(masks[i]))
            separation = (max(
                (float(np.linalg.norm(centers[i]-centers[j])) for j in selected),
                default=0.
            ))
            if not selected:
                return (additional, projected_sampling[i], base, -i)
            return (additional, min(separation/radius, 1.),
                    projected_sampling[i], base, -i)
        winner = max((i for i in valid if i not in selected), key=quality)
        # Once two independent sources are retained for redundancy, do not
        # decode further photos that provide ZERO new supported/visible roof
        # samples. A fifth-to-eighth source is justified ONLY by actual
        # additional fitted geometry coverage, never by baseline alone.
        if (len(selected) >= 2
                and not np.any(masks[winner] & ~covered)):
            break
        selected.append(winner)
        covered |= masks[winner]
        if len(selected) >= 2 and np.all(covered):
            break
    return tuple(selected)


@dataclass(frozen=True)
class PrivateRGBMultiPlaneOrthopreview:
    rgb_private: np.ndarray
    valid_mask_private: np.ndarray
    ambiguous_overlap_mask_private: np.ndarray
    selected_plane_index_private: np.ndarray
    top_left_xy_enu_private_m: tuple[float, float]
    meters_per_pixel: float
    plane_count: int
    source_camera_counts: tuple[int, ...]
    ambiguous_overlap_pixels: int
    valid_pixel_count: int
    state: str = "private_multi_pitched_3d_rgb_preview_unverified"
    radiometric_corrected_source_count: int = 0
    radiometric_overlap_support_pixels: int = 0
    candidate_camera_seam_boundary_pairs: int = 0
    worst_candidate_camera_seam_rgb_jump_p95: float | None = None
    candidate_facet_transition_boundary_pairs: int = 0
    candidate_facet_transition_rgb_jump_p95: float | None = None
    unsupported_convex_hull_pixels: int = 0

    def privacy_safe_summary(self) -> dict:
        total = int(self.valid_mask_private.size)
        return {
            "status": self.state,
            "plane_candidate_count": self.plane_count,
            "width_px": int(self.rgb_private.shape[1]),
            "height_px": int(self.rgb_private.shape[0]),
            "source_cameras_min": min(self.source_camera_counts),
            "source_cameras_max": max(self.source_camera_counts),
            "valid_pixel_count": self.valid_pixel_count,
            "radiometric_corrected_source_count": (
                self.radiometric_corrected_source_count
            ),
            "radiometric_overlap_support_pixels": (
                self.radiometric_overlap_support_pixels
            ),
            "candidate_camera_seam_boundary_pairs": (
                self.candidate_camera_seam_boundary_pairs
            ),
            "worst_candidate_camera_seam_rgb_jump_p95": (
                self.worst_candidate_camera_seam_rgb_jump_p95
            ),
            "candidate_facet_transition_boundary_pairs": (
                self.candidate_facet_transition_boundary_pairs
            ),
            "candidate_facet_transition_rgb_jump_p95": (
                self.candidate_facet_transition_rgb_jump_p95
            ),
            "unsupported_convex_hull_pixels": self.unsupported_convex_hull_pixels,
            "valid_fraction_of_union_bbox": self.valid_pixel_count/total,
            "ambiguous_plane_overlap_pixels": self.ambiguous_overlap_pixels,
            "ambiguous_fraction_of_union_bbox": self.ambiguous_overlap_pixels/total,
            "roof_surface_identity_verified": False,
            "roof_geometry_verified": False,
            "independent_survey_verified": False,
            "orthophoto_verified": False,
        }


def compose_private_pitched_rgb_orthopatches(
    planes: tuple[PrivateRGBPitchedPlaneCandidate, ...],
    patches: tuple[PrivateRGBPitchedPlaneOrthopatch, ...],
    *,
    overlap_height_tolerance_m: float = .15,
    max_side: int = 2048,
    should_cancel=None,
) -> PrivateRGBMultiPlaneOrthopreview:
    """Place independent pitched patches on one north-up ENU grid.

    Pixel priority is highest candidate plane Z only if it is clearly above
    other candidates. Similar-height overlap stays INVALID/ambiguous to avoid
    manufacturing roof ridges or false seam-free orthophotos.
    """
    if should_cancel is not None and should_cancel():
        raise RuntimeError("private multi-plane RGB composition cancelled")
    if (type(planes) is not tuple or type(patches) is not tuple
            or not 2 <= len(planes) <= 6 or len(planes) != len(patches)
            or any(not isinstance(p, PrivateRGBPitchedPlaneCandidate) for p in planes)
            or any(not isinstance(p, PrivateRGBPitchedPlaneOrthopatch) for p in patches)
            or type(overlap_height_tolerance_m) not in (int, float)
            or not np.isfinite(overlap_height_tolerance_m)
            or not .025 <= overlap_height_tolerance_m <= .5
            or type(max_side) is not int or not 64 <= max_side <= 2048):
        raise ValueError("bounded multiple private pitched orthopatches required")
    resolution = float(patches[0].meters_per_pixel)
    if (not np.isfinite(resolution) or not .01 <= resolution <= .5
            or any(not np.isclose(p.meters_per_pixel, resolution, atol=1.e-10)
                   for p in patches)):
        raise ValueError("pitch patches must share a common metric resolution")
    hulls = tuple(np.asarray(p.footprint_xy_private_m, dtype=np.float64)
                  for p in planes)
    if any(h.ndim != 2 or h.shape[1] != 2 or len(h) < 3
           or not np.isfinite(h).all() for h in hulls):
        raise ValueError("valid private candidate hulls required")
    min_x = min(float(h[:, 0].min()) for h in hulls)
    max_x = max(float(h[:, 0].max()) for h in hulls)
    min_y = min(float(h[:, 1].min()) for h in hulls)
    max_y = max(float(h[:, 1].max()) for h in hulls)
    width = int(np.ceil((max_x-min_x)/resolution))
    height = int(np.ceil((max_y-min_y)/resolution))
    if (width < 2 or height < 2 or width > max_side or height > max_side
            or width*height > 2_000_000):
        raise ValueError("private multi-plane RGB canvas exceeds resource budget")
    xx, yy = np.meshgrid(
        min_x + (np.arange(width)+.5)*resolution,
        max_y - (np.arange(height)+.5)*resolution,
    )
    rgb = np.zeros((height,width,3), dtype=np.uint8)
    winner = np.full((height,width), -1, dtype=np.int16)
    highest = np.full((height,width), -np.inf)
    second = np.full((height,width), -np.inf)
    coverage = np.zeros((height,width), dtype=np.uint8)
    for index, (plane, patch, hull) in enumerate(zip(planes, patches, hulls)):
        if should_cancel is not None and should_cancel():
            raise RuntimeError("private multi-plane RGB composition cancelled")
        if (not isinstance(patch.rgb_private, np.ndarray)
                or not isinstance(patch.valid_mask_private, np.ndarray)
                or patch.rgb_private.ndim != 3
                or patch.rgb_private.shape[2] != 3
                or patch.rgb_private.dtype != np.uint8
                or patch.valid_mask_private.dtype != bool
                or patch.valid_mask_private.shape != patch.rgb_private.shape[:2]
                or not np.isfinite(patch.top_left_xy_enu_private_m).all()
                or patch.source_camera_count < 1
                or not np.isclose(patch.top_left_xy_enu_private_m[0],
                                  float(hull[:, 0].min()), atol=1.e-6)
                or not np.isclose(patch.top_left_xy_enu_private_m[1],
                                  float(hull[:, 1].max()), atol=1.e-6)):
            raise ValueError("misaligned or malformed private pitched RGB patch")
        n = np.asarray(plane.normal_enu_private, dtype=np.float64)
        off = float(plane.signed_offset_enu_private_m)
        if (n.shape != (3,) or not np.isfinite(n).all()
                or not np.isclose(np.linalg.norm(n), 1., atol=1.e-4)
                or n[2] <= .1 or not np.isfinite(off)):
            raise ValueError("invalid private pitched plane for common canvas")
        local_x = ((xx - patch.top_left_xy_enu_private_m[0])/resolution -.5
                   ).astype(np.float32)
        local_y = ((patch.top_left_xy_enu_private_m[1] - yy)/resolution -.5
                   ).astype(np.float32)
        # Nearest-neighbour is deliberately used for both RGB and support
        # mask to prevent interpolation across a missing-data roof edge.
        sampled = cv2.remap(
            patch.rgb_private, local_x, local_y,
            cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0,0,0),
        )
        supported = cv2.remap(
            patch.valid_mask_private.astype(np.uint8),
            local_x, local_y, cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        ).astype(bool)
        # A patch was masked at its OWN exact metric pixel centers.
        # Remapping its binary mask by nearest neighbour onto a shifted
        # common ENU grid can nevertheless paint a DIFFERENT global pixel
        # center just outside the fitted facet hull. Enforce the true
        # convex polygon again at the FINAL output pixel centers, before
        # deciding coverage, facet height, RGB priority or seams.
        area2 = float(np.sum(
            hull[:, 0] * np.roll(hull[:, 1], -1)
            - np.roll(hull[:, 0], -1) * hull[:, 1]
        ))
        if not np.isfinite(area2) or abs(area2) <= 1.e-10:
            raise ValueError("degenerate private pitched plane footprint")
        indices = np.flatnonzero(supported)
        if len(indices):
            xs = xx.ravel()[indices]
            ys = yy.ravel()[indices]
            sign = 1. if area2 > 0 else -1.
            inside = np.ones(len(indices), dtype=bool)
            for vertex, edge in zip(hull, np.roll(hull, -1, axis=0)-hull):
                cross = edge[0]*(ys-vertex[1]) - edge[1]*(xs-vertex[0])
                inside &= sign*cross >= -1.e-8
                if not np.any(inside):
                    break
            supported.ravel()[indices[~inside]] = False
        z = (-off - n[0]*xx - n[1]*yy)/n[2]
        coverage += supported.astype(np.uint8)
        above = supported & (z > highest)
        second = np.where(above, highest, np.where(supported & (z > second),
                                                  z, second))
        highest = np.where(above, z, highest)
        rgb[above] = sampled[above]
        winner[above] = index
    # Adjacent matched roof facets may meet at the same ridge height.
    # Such overlaps cannot be disambiguated without true roof boundaries.
    ambiguous = (coverage >= 2) & (
        highest-second <= overlap_height_tolerance_m
    )
    valid = (coverage > 0) & ~ambiguous
    rgb[~valid] = 0
    winner[~valid] = -1
    facet_border_count, facet_border_p95 = _private_label_transition_rgb_jump(
        rgb, winner, valid,
    )
    camera_p95_values = [
        p.candidate_camera_seam_rgb_jump_p95 for p in patches
        if p.candidate_camera_seam_boundary_pairs > 0
        and p.candidate_camera_seam_rgb_jump_p95 is not None
    ]
    for array in (rgb, valid, ambiguous, winner):
        array.setflags(write=False)
    return PrivateRGBMultiPlaneOrthopreview(
        rgb, valid, ambiguous, winner,
        (min_x,max_y), resolution, len(planes),
        tuple(p.source_camera_count for p in patches),
        int(np.count_nonzero(ambiguous)), int(np.count_nonzero(valid)),
        radiometric_corrected_source_count=sum(
            p.radiometric_corrected_source_count for p in patches
        ),
        radiometric_overlap_support_pixels=sum(
            p.radiometric_overlap_support_pixels for p in patches
        ),
        candidate_camera_seam_boundary_pairs=sum(
            p.candidate_camera_seam_boundary_pairs for p in patches
        ),
        worst_candidate_camera_seam_rgb_jump_p95=(
            max(camera_p95_values) if camera_p95_values else None
        ),
        candidate_facet_transition_boundary_pairs=facet_border_count,
        candidate_facet_transition_rgb_jump_p95=facet_border_p95,
        unsupported_convex_hull_pixels=sum(
            p.unsupported_convex_hull_pixels for p in patches
        ),
    )
