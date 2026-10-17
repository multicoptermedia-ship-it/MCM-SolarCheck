"""Local, non-metric image-to-image overlap evidence for DJI flight archives.

ORB/RANSAC matches are diagnostics, not surveyed control points or roof coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
import re
from zipfile import ZipFile

_PATTERN = re.compile(r"DJI_(\d{14})_(\d{4})_([TV])\.JPG", re.IGNORECASE)


@dataclass(frozen=True)
class ImageTransition:
    first_id: str
    second_id: str
    matches: int
    inliers: int
    inlier_ratio: float
    occupied_inlier_cells: int = 0


@dataclass(frozen=True)
class FlightOverlapAudit:
    rgb: tuple[ImageTransition, ...]
    thermal: tuple[ImageTransition, ...]
    diagnostics: tuple[str, ...]

    @property
    def metric_roof_coverage_verified(self) -> bool:
        return False


def audit_flight_overlap(path, *, max_image_bytes=80_000_000, max_frames=200, max_side=800):
    """Read local JPEGs; compute adjacent ORB correspondences and RANSAC inliers."""
    import cv2
    import numpy as np
    from mcm_solarcheck.services.flight_zip_preflight import inspect_dji_flight_zip

    if max_side < 128 or max_frames < 2 or max_image_bytes <= 0:
        raise ValueError("invalid overlap resource limits")
    inspect_dji_flight_zip(path)
    entries = {"V": [], "T": []}
    with ZipFile(path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            match = _PATTERN.fullmatch(PurePosixPath(member.filename).name)
            if match:
                stamp, number, mode = match.groups()
                entries[mode.upper()].append((stamp, number, member))
        if sum(map(len, entries.values())) > max_frames:
            raise ValueError("flight exceeds overlap frame limit")
        orb = cv2.ORB_create(nfeatures=1400)
        matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
        results = {}
        from mcm_solarcheck.services.flight_inlier_distribution import assess_inlier_distribution
        for mode in ("V", "T"):
            frames = []
            for stamp, number, member in sorted(entries[mode], key=lambda item: (item[0], item[1])):
                if member.file_size > max_image_bytes:
                    raise ValueError("image exceeds overlap size limit")
                with archive.open(member) as stream:
                    data = stream.read(max_image_bytes + 1)
                if len(data) > max_image_bytes:
                    raise ValueError("image exceeds overlap size limit")
                array = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_GRAYSCALE)
                if array is None:
                    raise ValueError("unreadable image for overlap audit")
                h, w = array.shape
                scale = min(1.0, max_side / max(h, w))
                if scale < 1:
                    array = cv2.resize(array, (max(1, round(w * scale)), max(1, round(h * scale))))
                points, descriptors = orb.detectAndCompute(array, None)
                frames.append((number, points, descriptors, array.shape[1], array.shape[0]))
            transitions = []
            for (a_id, a_points, a_desc, width, height), (b_id, b_points, b_desc, _, _) in zip(frames, frames[1:]):
                good = []
                if a_desc is not None and b_desc is not None and len(a_desc) >= 2 and len(b_desc) >= 2:
                    for pair in matcher.knnMatch(a_desc, b_desc, k=2):
                        if len(pair) == 2 and pair[0].distance < 0.75 * pair[1].distance:
                            good.append(pair[0])
                inliers = 0
                occupied = 0
                if len(good) >= 4:
                    src = np.float32([a_points[m.queryIdx].pt for m in good])
                    dst = np.float32([b_points[m.trainIdx].pt for m in good])
                    _, mask = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
                    if mask is not None:
                        accepted = mask.ravel().astype(bool)
                        inliers = int(accepted.sum())
                        occupied = assess_inlier_distribution(src[accepted], width, height).occupied_cells
                transitions.append(ImageTransition(a_id, b_id, len(good), inliers, inliers / len(good) if good else 0.0, occupied))
            results[mode] = tuple(transitions)
    notes = ["adjacent image matches do not prove full roof coverage or metric accuracy"]
    if any(t.inliers < 10 for t in results["V"] + results["T"]):
        notes.append("weak image transition: fewer than 10 RANSAC inliers")
    notes.append("grid cell fraction is not roof area coverage")
    notes.append("independent camera calibration, surveyed roof plane and verified common reference required")
    return FlightOverlapAudit(results["V"], results["T"], tuple(notes))
