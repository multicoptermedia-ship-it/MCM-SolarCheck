"""In-memory inverse projection of RGB onto a PRIVATE pitched 3D plane.

World ENU XY output grid -> fitted plane height -> final calibrated camera
pose -> bilinear UNDISTORTED source RGB pixels. Unlike a 2D stitch, every
output sample is anchored on a different 3D plane point. Not a surveyed roof,
full physical visibility solver, radiometric seam correction or final orthophoto.
Optional candidate-plane ray intersections reject source views geometrically
occluded by OTHER fitted facets; unknown structures remain unmodeled.
No image, location, plane, source IDs or coordinates are serialized.
"""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from mcm_solarcheck.services.module_plane_projection import PinholeIntrinsics
from mcm_solarcheck.services.rgb_private_pitched_plane_candidates import (
    PrivateRGBPitchedPlaneCandidate,
)


@dataclass(frozen=True)
class PrivateRGBPitchedPlaneOrthopatch:
    rgb_private: np.ndarray
    valid_mask_private: np.ndarray
    top_left_xy_enu_private_m: tuple[float, float]
    meters_per_pixel: float
    source_camera_count: int
    planar_pixel_count: int
    valid_pixel_count: int
    multi_camera_pixel_count: int
    state: str = "private_pitched_rgb_orthopatch_unverified"
    candidate_occluded_source_pixels: int = 0
    secondary_source_pixel_count: int = 0
    source_fusion: str = "mean"
    radiometric_corrected_source_count: int = 0
    radiometric_overlap_support_pixels: int = 0

    def privacy_safe_summary(self) -> dict:
        return {
            "status": self.state,
            "width_px": int(self.rgb_private.shape[1]),
            "height_px": int(self.rgb_private.shape[0]),
            "source_camera_count": self.source_camera_count,
            "candidate_occluded_source_pixels": self.candidate_occluded_source_pixels,
            "secondary_source_pixel_count": self.secondary_source_pixel_count,
            "source_fusion": self.source_fusion,
            "radiometric_corrected_source_count": (
                self.radiometric_corrected_source_count
            ),
            "radiometric_overlap_support_pixels": (
                self.radiometric_overlap_support_pixels
            ),
            "planar_pixel_count": self.planar_pixel_count,
            "valid_pixel_count": self.valid_pixel_count,
            "multi_camera_pixel_count": self.multi_camera_pixel_count,
            "footprint_coverage_fraction": (
                self.valid_pixel_count / self.planar_pixel_count
            ),
            "multi_camera_coverage_fraction": (
                self.multi_camera_pixel_count / self.planar_pixel_count
            ),
            "independent_survey_verified": False,
            "roof_geometry_verified": False,
            "roof_surface_identity_verified": False,
            "orthophoto_verified": False,
        }


def _candidate_plane_occlusion_mask(
    points_enu: np.ndarray,
    camera_center_enu: np.ndarray,
    eligible: np.ndarray,
    other_planes: tuple[PrivateRGBPitchedPlaneCandidate, ...],
    *,
    should_cancel=None,
) -> np.ndarray:
    """Return source rays blocked by other finite fitted candidate facets.

    Intersect C+t(P-C) with each other candidate plane for 0<t<1, then
    require the intersection inside its convex footprint. Geometric model
    only: missing structures and true photographed visibility are unknown.
    """
    blocked = np.zeros(len(points_enu), dtype=bool)
    if not other_planes or not np.any(eligible):
        return blocked
    rays = points_enu - camera_center_enu
    for plane in other_planes:
        if should_cancel is not None and should_cancel():
            raise RuntimeError("private candidate ray-visibility cancelled")
        n = np.asarray(plane.normal_enu_private, dtype=np.float64)
        polygon = np.asarray(plane.footprint_xy_private_m, dtype=np.float64)
        offset = float(plane.signed_offset_enu_private_m)
        if (n.shape != (3,) or polygon.ndim != 2
                or polygon.shape[1:] != (2,)
                or not 3 <= len(polygon) <= 200000
                or not np.isfinite(n).all() or not np.isfinite(polygon).all()
                or not np.isfinite(offset)
                or not np.isclose(np.linalg.norm(n), 1., atol=1.e-4)
                or n[2] <= .1):
            raise ValueError("invalid private occluding plane candidate")
        denominator = rays @ n
        numerator = -(float(camera_center_enu @ n) + offset)
        indices = np.flatnonzero(
            eligible & ~blocked & (np.abs(denominator) > 1.e-10)
        )
        if not len(indices):
            continue
        distances = numerator / denominator[indices]
        between = (np.isfinite(distances)
                   & (distances > 1.e-6) & (distances < 1.-1.e-6))
        indices, distances = indices[between], distances[between]
        if not len(indices):
            continue
        hit_xy = (camera_center_enu[:2]
                  + distances[:, None]*rays[indices, :2])
        edges = np.roll(polygon, -1, axis=0) - polygon
        area2 = float(np.sum(
            polygon[:, 0]*np.roll(polygon[:, 1], -1)
            - np.roll(polygon[:, 0], -1)*polygon[:, 1]
        ))
        if not np.isfinite(area2) or abs(area2) <= 1.e-10:
            raise ValueError("invalid private occluder convex footprint")
        sign = 1. if area2 > 0 else -1.
        inside = np.ones(len(indices), dtype=bool)
        for vertex, edge in zip(polygon, edges):
            cross = (edge[0]*(hit_xy[:, 1]-vertex[1])
                     - edge[1]*(hit_xy[:, 0]-vertex[0]))
            inside &= sign*cross >= -1.e-8
            if not np.any(inside):
                break
        blocked[indices[inside]] = True
    return blocked



def _private_robust_overlap_color_offset(
    reference_rgb: np.ndarray,
    candidate_rgb: np.ndarray,
    reference_valid: np.ndarray,
    candidate_valid: np.ndarray,
    height: int,
    width: int,
) -> tuple[np.ndarray, int] | None:
    """Estimate a conservative RGB OFFSET from matching valid roof pixels.

    Reference is the already-selected camera mosaic. Sample only actual
    geometrical overlap, away from coverage edges and camera saturation.
    Large illumination disagreements and geometrically unstable differences
    are left UNCORRECTED, never silently declared seam-free.
    """
    common = (reference_valid & candidate_valid).reshape(height, width)
    # Erode away uncertain interpolation/visibility boundaries.
    core = cv2.erode(
        common.astype(np.uint8),
        np.ones((3, 3), dtype=np.uint8),
        iterations=1, borderType=cv2.BORDER_CONSTANT,
        borderValue=0,
    ).ravel().astype(bool)
    indices = np.flatnonzero(core)
    if len(indices) < 128:
        return None
    if len(indices) > 4096:
        indices = indices[np.linspace(
            0, len(indices)-1, 4096, dtype=np.intp,
        )]
    reference = reference_rgb[indices].astype(np.int16)
    candidate = candidate_rgb[indices].astype(np.int16)
    # Midtones constrain exposure offsets better than clipped PV/sky pixels.
    unsaturated = np.all(
        (reference >= 8) & (reference <= 247)
        & (candidate >= 8) & (candidate <= 247),
        axis=1,
    )
    reference, candidate = reference[unsaturated], candidate[unsaturated]
    if len(reference) < 128:
        return None
    differences = reference - candidate
    shift = np.median(differences, axis=0)
    mad = np.median(np.abs(differences-shift), axis=0)
    # Do not force alignment where perspective errors, reflections or large
    # scene differences make a single channel offset untrustworthy.
    if np.any(np.abs(shift) > 24.) or np.any(mad > 12.):
        return None
    return np.rint(shift).astype(np.int16), int(len(reference))


def render_private_pitched_rgb_orthopatch(
    plane: PrivateRGBPitchedPlaneCandidate,
    undistorted_rgb_images: tuple[np.ndarray, ...],
    world_enu_to_camera_poses: tuple[np.ndarray, ...],
    intrinsics: PinholeIntrinsics,
    *,
    meters_per_pixel: float = .05,
    max_side: int = 1024,
    occluder_planes: tuple[PrivateRGBPitchedPlaneCandidate, ...] = (),
    source_fusion: str = "mean",
    should_cancel=None,
) -> PrivateRGBPitchedPlaneOrthopatch:
    """Render an ENU-north-up, pitched-plane preview; no disk writes.

    INPUT RGB IMAGES MUST ALREADY BE UNDISTORTED at the exact intrinsics
    resolution. No Gimbal/EXIF-derived camera orientation, no 2D homography
    over the entire flight, no blending of unrelated physical surfaces.
    'priority' selects exactly one source per pixel: first eligible camera
    in the geometric ranking, with fallback when the primary is not visible.
    This suppresses multiview averaging ghosting, but does NOT guarantee
    radiometric seam alignment or optimal local sharpness.
    'priority_overlap' additionally estimates a small robust color offset
    from genuine 3D-projected same-plane overlap before filling uncovered
    pixels. If there is no stable overlap, use the source UNCORRECTED.
    """
    if should_cancel is not None and should_cancel():
        raise RuntimeError("private pitched RGB projection cancelled")
    if (not isinstance(plane, PrivateRGBPitchedPlaneCandidate)
            or not isinstance(intrinsics, PinholeIntrinsics)
            or type(undistorted_rgb_images) is not tuple
            or type(world_enu_to_camera_poses) is not tuple
            or not 1 <= len(undistorted_rgb_images) <= 8
            or len(undistorted_rgb_images) != len(world_enu_to_camera_poses)
            or type(meters_per_pixel) not in (int, float)
            or not np.isfinite(meters_per_pixel)
            or not .01 <= meters_per_pixel <= .50
            or type(max_side) is not int or not 64 <= max_side <= 2048
            or source_fusion not in (
                "mean", "priority", "priority_overlap"
            )
            or type(occluder_planes) is not tuple or len(occluder_planes) > 5
            or any(not isinstance(p, PrivateRGBPitchedPlaneCandidate)
                   for p in occluder_planes)):
        raise ValueError("bounded private pitched-plane projection inputs required")

    n = np.asarray(plane.normal_enu_private, dtype=np.float64)
    hull = np.asarray(plane.footprint_xy_private_m, dtype=np.float64)
    offset = plane.signed_offset_enu_private_m
    k = np.asarray(
        [intrinsics.fx, intrinsics.fy, intrinsics.cx, intrinsics.cy],
        dtype=np.float64,
    )
    if (n.shape != (3,) or hull.ndim != 2 or hull.shape[1:] != (2,)
            or not 3 <= len(hull) <= 200000 or not np.isfinite(n).all()
            or not np.isfinite(hull).all() or not np.isfinite(offset)
            or not np.isfinite(k).all() or np.any(k[:2] <= 0)
            or n[2] <= .1 or not np.isclose(np.linalg.norm(n), 1., atol=1e-4)
            or not np.isfinite(plane.footprint_area_m2)
            or plane.footprint_area_m2 <= 0):
        raise ValueError("invalid private pitched plane/intrinsics geometry")
    minimum = np.min(hull, axis=0)
    maximum = np.max(hull, axis=0)
    dx, dy = maximum - minimum
    width = int(np.ceil(dx / meters_per_pixel))
    height = int(np.ceil(dy / meters_per_pixel))
    if (width < 2 or height < 2 or width > max_side or height > max_side
            or width * height > 2_000_000):
        raise ValueError("private orthopatch resolution exceeds resource budget")

    # north-up output: column j corresponds to east+, row i to north-.
    xs = minimum[0] + (np.arange(width) + .5) * meters_per_pixel
    ys = maximum[1] - (np.arange(height) + .5) * meters_per_pixel
    xx, yy = np.meshgrid(xs, ys)
    points = np.column_stack((
        xx.ravel(), yy.ravel(),
        (-offset - n[0]*xx.ravel() - n[1]*yy.ravel()) / n[2],
    ))
    # The convex hull is NOT a verified real roof boundary; keep ALL samples
    # outside this provisional inlier footprint strictly transparent/invalid.
    poly = np.column_stack((
        (hull[:, 0] - minimum[0]) / meters_per_pixel - .5,
        (maximum[1] - hull[:, 1]) / meters_per_pixel - .5,
    ))
    footprint_mask = np.zeros((height, width), np.uint8)
    cv2.fillConvexPoly(
        footprint_mask, np.round(poly).astype(np.int32), 1,
    )
    footprint = footprint_mask.ravel().astype(bool)
    planar_count = int(np.count_nonzero(footprint))
    if planar_count < 4:
        raise ValueError("private pitched plane has no usable raster footprint")
    rgb_sum = np.zeros((height*width, 3), dtype=np.float64)
    weights = np.zeros(height*width, dtype=np.float64)
    views = np.zeros(height*width, dtype=np.uint8)
    priority_rgb = np.zeros((height*width, 3), dtype=np.uint8)
    priority_covered = np.zeros(height*width, dtype=bool)
    secondary_pixel_count = 0
    candidate_occluded = 0
    radiometric_corrected = 0
    radiometric_support = 0
    for source_index, (image, pose) in enumerate(zip(
        undistorted_rgb_images, world_enu_to_camera_poses
    )):

        if should_cancel is not None and should_cancel():
            raise RuntimeError("private pitched RGB projection cancelled")
        if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
                or image.ndim != 3 or image.shape[2] != 3
                or not 32 <= image.shape[0] <= 6000
                or not 32 <= image.shape[1] <= 8000):
            raise ValueError("full-size undistorted RGB camera image required")
        camera = np.asarray(pose, dtype=np.float64)
        if camera.shape != (3,4) or not np.isfinite(camera).all():
            raise ValueError("finite fitted ENU-to-camera extrinsics required")
        rot, tr = camera[:, :3], camera[:, 3]
        if (not np.allclose(rot.T @ rot, np.eye(3), atol=1e-4)
                or not np.isclose(np.linalg.det(rot), 1., atol=1e-4)):
            raise ValueError("proper final fitted RGB camera rotation required")
        local = points @ rot.T + tr
        depth = local[:, 2]
        z = np.where(depth > 1e-8, depth, 1.)
        u = k[0] * local[:, 0] / z + k[2]
        v = k[1] * local[:, 1] / z + k[3]
        in_image = (
            footprint & np.isfinite(u) & np.isfinite(v)
            & (depth > 1e-8)
            & (u >= 0) & (v >= 0)
            & (u < image.shape[1]-1) & (v < image.shape[0]-1)
        )
        if not np.any(in_image):
            continue
        if occluder_planes:
            blocked = _candidate_plane_occlusion_mask(
                points, -(rot.T @ tr), in_image, occluder_planes,
                should_cancel=should_cancel,
            )
            candidate_occluded += int(np.count_nonzero(blocked))
            in_image &= ~blocked
        if not np.any(in_image):
            continue
        # Invalid remap entries point to a harmless constant; they NEVER
        # contribute via the separate in_image mask.
        mx = np.where(in_image, u, 0).astype(np.float32).reshape(height,width)
        my = np.where(in_image, v, 0).astype(np.float32).reshape(height,width)
        sampled = cv2.remap(
            image, mx, my, interpolation=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT, borderValue=(0,0,0),
        ).reshape(-1,3)
        # Count the eligible physical source candidates separately from the
        # final single-source choice. Reprojection and occlusion masks both
        # apply BEFORE making a choice; no hidden pixels can fill a gap.
        views[in_image] += 1
        if source_fusion in ("priority", "priority_overlap"):
            # The upstream camera selector orders sources by whole-plane
            # coverage/baseline. One stable primary minimizes internal seams;
            # later cameras fill only genuinely missing/occluded samples.
            newly_covered = in_image & ~priority_covered
            if np.any(newly_covered):
                incoming = sampled
                if source_fusion == "priority_overlap" and source_index:
                    estimate = _private_robust_overlap_color_offset(
                        priority_rgb, sampled, priority_covered, in_image,
                        height, width,
                    )
                    if estimate is not None:
                        shift, support = estimate
                        incoming = np.clip(
                            sampled.astype(np.int16) + shift[None, :],
                            0, 255,
                        ).astype(np.uint8)
                        radiometric_corrected += 1
                        radiometric_support += support
                priority_rgb[newly_covered] = incoming[newly_covered]
                priority_covered[newly_covered] = True
                if source_index:
                    secondary_pixel_count += int(
                        np.count_nonzero(newly_covered)
                    )
        else:
            rgb_sum[in_image] += sampled[in_image]
            weights[in_image] += 1.
    if source_fusion in ("priority", "priority_overlap"):
        covered = priority_covered
        rgb = priority_rgb
    else:
        covered = weights > 0
        rgb = np.zeros((height*width,3), dtype=np.uint8)
        if np.any(covered):
            rgb[covered] = np.rint(
                rgb_sum[covered] / weights[covered, None]
            ).clip(0,255).astype(np.uint8)
    rgb = rgb.reshape(height,width,3)
    mask = covered.reshape(height,width)
    for array in (rgb,mask):
        array.setflags(write=False)
    return PrivateRGBPitchedPlaneOrthopatch(
        rgb, mask, (float(minimum[0]),float(maximum[1])),
        float(meters_per_pixel), len(undistorted_rgb_images),
        planar_count, int(np.count_nonzero(covered)),
        int(np.count_nonzero(views >= 2)),
        candidate_occluded_source_pixels=candidate_occluded,
        secondary_source_pixel_count=secondary_pixel_count,
        source_fusion=source_fusion,
        radiometric_corrected_source_count=radiometric_corrected,
        radiometric_overlap_support_pixels=radiometric_support,
    )
