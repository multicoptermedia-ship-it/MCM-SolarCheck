"""Private post-BA multiview parallax audit before any roof-surface geometry.

Pixel residuals and two-camera observation counts alone cannot establish
stable 3D triangulation. Measure a conservative viewing-ray angle per landmark
in the fitted (private) camera frame; only count/percentile summaries may leave
memory. This does not prove survey accuracy, roof faces or orthophotos.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class RGBMultiviewParallaxAudit:
    camera_count: int
    landmark_count: int
    observation_count: int
    minimum_parallax_deg: float
    minimum_supported_landmark_fraction: float
    supported_landmark_count: int
    weak_landmark_count: int
    observed_landmark_p10_parallax_deg: float
    observed_landmark_median_parallax_deg: float

    def privacy_safe_summary(self) -> dict:
        return {
            "schema": "mcm.private_rgb_multiview_parallax_audit.v1",
            "parallax_audit_completed": True,
            "camera_count": self.camera_count,
            "landmark_count": self.landmark_count,
            "observation_count": self.observation_count,
            "minimum_parallax_deg": self.minimum_parallax_deg,
            "minimum_supported_landmark_fraction": (
                self.minimum_supported_landmark_fraction
            ),
            "supported_landmark_count": self.supported_landmark_count,
            "weak_landmark_count": self.weak_landmark_count,
            "supported_landmark_fraction": (
                self.supported_landmark_count / self.landmark_count
            ),
            "landmark_parallax_p10_deg": (
                self.observed_landmark_p10_parallax_deg
            ),
            "landmark_parallax_median_deg": (
                self.observed_landmark_median_parallax_deg
            ),
            "parallax_quality_passed": (
                self.supported_landmark_count / self.landmark_count
                >= self.minimum_supported_landmark_fraction
            ),
            "independent_survey_verified": False,
            "roof_geometry_verified": False,
            "orthophoto_verified": False,
        }


class RGBMultiviewParallaxQualityError(ValueError):
    """Private rejection: never embed camera/frame IDs or metric coordinates."""

    def __init__(self, audit: RGBMultiviewParallaxAudit):
        if (not isinstance(audit, RGBMultiviewParallaxAudit)
                or audit.privacy_safe_summary()["parallax_quality_passed"]):
            raise ValueError("failed private multiview parallax audit required")
        self.audit = audit
        super().__init__("RGB multiview depth parallax quality gate failed")


def audit_rgb_multiview_parallax(
    poses_world_to_camera: tuple[np.ndarray, ...],
    landmarks_xyz: np.ndarray,
    observation_frame_indices: np.ndarray,
    observation_landmark_indices: np.ndarray,
    *,
    min_parallax_deg: float = 0.25,
    min_supported_landmark_fraction: float = 0.75,
    enforce_parallax: bool = True,
    should_cancel=None,
) -> RGBMultiviewParallaxAudit:
    """Check every landmark has at least two distinct cameras and ray separation.

    Per-landmark maximum angle relative to its FIRST observed camera is a
    conservative lower bound on the actual maximum inter-camera ray angle.
    A tiny lower bound fails closed; it never fabricates stronger parallax.
    Vectorized O(observations) storage and no image/coordinate exports.
    """
    if should_cancel is not None and should_cancel():
        raise RuntimeError("private RGB parallax audit cancelled")
    if (type(poses_world_to_camera) is not tuple
            or not 3 <= len(poses_world_to_camera) <= 1000
            or type(enforce_parallax) is not bool
            or type(min_parallax_deg) not in (int, float)
            or not np.isfinite(min_parallax_deg)
            or not 0.05 <= min_parallax_deg <= 5.
            or type(min_supported_landmark_fraction) not in (int, float)
            or not np.isfinite(min_supported_landmark_fraction)
            or not .5 <= min_supported_landmark_fraction <= 1.):
        raise ValueError("invalid bounded full-flight parallax policy")
    count = len(poses_world_to_camera)
    poses = np.asarray(poses_world_to_camera, dtype=np.float64)
    xyz = np.asarray(landmarks_xyz, dtype=np.float64)
    fid = np.asarray(observation_frame_indices)
    lid = np.asarray(observation_landmark_indices)
    if (poses.shape != (count, 3, 4) or xyz.ndim != 2
            or xyz.shape[1:] != (3,) or not 8 <= len(xyz) <= 200000
            or fid.ndim != 1 or lid.ndim != 1
            or not np.issubdtype(fid.dtype, np.integer)
            or not np.issubdtype(lid.dtype, np.integer)
            or not 24 <= len(fid) <= 800000 or len(lid) != len(fid)
            or np.any(fid < 0) or np.any(fid >= count)
            or np.any(lid < 0) or np.any(lid >= len(xyz))
            or not np.isfinite(poses).all() or not np.isfinite(xyz).all()):
        raise ValueError("invalid complete private multiview geometry")
    rotation = poses[:, :, :3]
    if (not np.allclose(np.matmul(rotation.transpose(0, 2, 1), rotation),
                         np.eye(3), atol=1e-4)
            or not np.allclose(np.linalg.det(rotation), 1., atol=1e-4)):
        raise ValueError("invalid camera rotations in private parallax audit")

    unique_pair = np.unique(lid.astype(np.int64) * count + fid.astype(np.int64))
    seen = np.bincount(unique_pair // count, minlength=len(xyz))
    if np.min(seen) < 2:
        raise ValueError("every 3D landmark needs two distinct camera views")

    centers = -np.einsum("nji,nj->ni", rotation, poses[:, :, 3])
    rays = xyz[lid] - centers[fid]
    length = np.linalg.norm(rays, axis=1)
    if not np.isfinite(length).all() or np.any(length <= 1e-8):
        raise ValueError("degenerate private camera to 3D point rays")
    rays /= length[:, None]
    # Deterministic first observation per landmark, even when the upstream
    # observation array is not ordered by landmark ID.
    present, first = np.unique(lid, return_index=True)
    if len(present) != len(xyz):
        raise ValueError("all retained RGB landmarks require observations")
    reference = np.empty_like(xyz)
    reference[present] = rays[first]
    cosine = np.einsum("ij,ij->i", rays, reference[lid])
    smallest_cosine = np.ones(len(xyz), dtype=np.float64)
    np.minimum.at(smallest_cosine, lid, np.clip(cosine, -1., 1.))
    angles = np.degrees(np.arccos(np.clip(smallest_cosine, -1., 1.)))
    if not np.isfinite(angles).all():
        raise ValueError("nonfinite private multiview viewing-ray angles")

    supported = int(np.count_nonzero(angles >= min_parallax_deg))
    audit = RGBMultiviewParallaxAudit(
        count, len(xyz), len(fid), float(min_parallax_deg),
        float(min_supported_landmark_fraction), supported,
        len(xyz) - supported, float(np.percentile(angles, 10)),
        float(np.median(angles)),
    )
    if enforce_parallax and not audit.privacy_safe_summary()["parallax_quality_passed"]:
        raise RGBMultiviewParallaxQualityError(audit)
    return audit
