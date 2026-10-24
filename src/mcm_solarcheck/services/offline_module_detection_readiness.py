"""Conservative offline RGB module-detection readiness inventory.

An imported RGB frame or metadata-only thermal/RGB pair is NOT a detected PV
module. This service inspects SQLite references only and creates no approvals,
model detections, or project outputs. All counters are project scoped.
"""
from __future__ import annotations

from dataclasses import dataclass

from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)


@dataclass(frozen=True)
class ModuleDetectionReadiness:
    rgb_frames: int
    geometrically_plausible_rgb: int
    imported_rgb_with_digest: int
    rgb_ready_as_detector_inputs: int
    rgb_missing_geometry: int
    rgb_missing_import_digest: int
    metadata_pairs: int
    no_verified_detector: bool
    changed_inputs: bool
    read_only: bool = True

    @property
    def can_run_full_module_analysis(self) -> bool:
        # No production-qualified segmentation detector is shipped or attested
        # by a stored file path, a pair count, or a caller-supplied model name.
        return False


def assess_module_detection_readiness(database, project_id: str):
    """Read SQLite-only eligibility, never original image bytes or GPS.

    RGB geometry and a recorded sha256 are *necessary* but not sufficient:
    bytes must later be verified again against the referenced original.
    """
    before = capture_offline_processing_inventory(database, project_id)
    with database.connect() as sql:
        frames = sql.execute(
            "SELECT f.width,f.height,t.content_sha256 FROM image_frames f "
            "LEFT JOIN training_samples t ON t.project_id=f.project_id "
            "AND t.source_frame_id=f.frame_id AND t.modality='rgb' "
            "WHERE f.project_id=? ORDER BY f.frame_id",
            (project_id,),
        ).fetchall()
    if len(frames) != before.rgb_frames:
        raise ValueError("RGB inventory changed during inspection")
    geom = digest = candidate = missing_geom = missing_digest = 0
    for width, height, sha in frames:
        valid_geometry = (
            type(width) is int and type(height) is int
            and width > 0 and height > 0
            and width * height <= 100_000_000
        )
        valid_hash = (
            isinstance(sha, str) and len(sha) == 64
            and all(c in "0123456789abcdefABCDEF" for c in sha)
        )
        geom += int(valid_geometry)
        digest += int(valid_hash)
        candidate += int(valid_geometry and valid_hash)
        missing_geom += int(not valid_geometry)
        missing_digest += int(not valid_hash)
    after = capture_offline_processing_inventory(database, project_id)
    return ModuleDetectionReadiness(
        rgb_frames=len(frames),
        geometrically_plausible_rgb=geom,
        imported_rgb_with_digest=digest,
        rgb_ready_as_detector_inputs=candidate,
        rgb_missing_geometry=missing_geom,
        rgb_missing_import_digest=missing_digest,
        metadata_pairs=before.image_pairs,
        no_verified_detector=True,
        changed_inputs=(before.fingerprint != after.fingerprint),
    )
