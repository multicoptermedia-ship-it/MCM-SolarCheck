"""Opt-in, local and read-only control-point assessment for one stored pair.

The caller must supply independently checked fit/holdout correspondences.
Accepting a homography holdout does NOT authorize pixels, reports or diagnoses.
No original images, project/customer identifiers, GPS or point arrays are logged.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from math import isfinite
from pathlib import Path

from mcm_solarcheck.pairing.registration import ControlPoint, estimate_homography


@dataclass(frozen=True)
class PairControlPointCheck:
    status: str
    reason: str
    fit_points: int
    fit_inliers: int
    holdout_points: int
    holdout_rms_px: float | None
    holdout_max_px: float | None
    registration_approved: bool = False
    report_approved: bool = False


def _read_points(value, name: str) -> tuple[ControlPoint, ...]:
    if not isinstance(value, list) or len(value) > 250:
        raise ValueError("Control-point collection must be a bounded array")
    points = []
    for row in value:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("Control points must use four coordinates")
        if any(type(x) not in (int, float) or not isfinite(x) for x in row):
            raise ValueError("Control coordinates must be finite numbers")
        points.append(ControlPoint(*(float(x) for x in row)))
    return tuple(points)


def check_project_pair_control_points(
    database, project_id: str, path: str | Path,
) -> PairControlPointCheck:
    """Recheck one explicit local JSON against existing project/pair identity.

    The JSON's pair_id must exist in the active project. Sensor pixel dimensions
    come from SQLite rather than from the untrusted JSON. No database writes.
    """
    source = Path(path)
    if (source.suffix.lower() != ".json" or source.is_symlink()
            or not source.is_file() or source.stat().st_size > 128_000):
        raise ValueError("Existing small local control-point JSON required")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeError, OSError, ValueError) as exc:
        raise ValueError("Invalid control-point JSON") from exc
    if not isinstance(payload, dict) or payload.get("schema") != 1:
        raise ValueError("Unsupported control-point schema")
    pair_id = payload.get("pair_id")
    if not isinstance(pair_id, str) or not pair_id or len(pair_id) > 200:
        raise ValueError("Explicit stored pair ID required")
    fit = _read_points(payload.get("fit_points"), "fit_points")
    holdout = _read_points(payload.get("holdout_points"), "holdout_points")

    with database.connect() as db:
        row = db.execute("""
            SELECT r.width AS rgb_width, r.height AS rgb_height,
                   t.width AS thermal_width, t.height AS thermal_height
              FROM image_pairs AS p
              JOIN image_frames AS r
                ON r.project_id=p.project_id AND r.frame_id=p.rgb_frame_id
              JOIN thermal_frames AS t
                ON t.project_id=p.project_id AND t.frame_id=p.thermal_frame_id
             WHERE p.project_id=? AND p.pair_id=?
        """, (project_id, pair_id)).fetchone()
    if row is None:
        raise ValueError("Stored pair not found in active project")
    sizes = tuple(row[x] for x in (
        "thermal_width", "thermal_height", "rgb_width", "rgb_height"
    ))
    if any(type(x) is not int or x < 2 or x > 30000 for x in sizes):
        raise ValueError("Recorded sensor dimensions unavailable")
    estimate = estimate_homography(
        fit, holdout, thermal_size=sizes[:2], rgb_size=sizes[2:],
    )
    accepted = bool(estimate.quality.validated)
    return PairControlPointCheck(
        status="holdout_passed_unapproved" if accepted else "refused",
        reason=estimate.quality.reason,
        fit_points=estimate.fit_points,
        fit_inliers=estimate.inliers,
        holdout_points=estimate.quality.control_points,
        holdout_rms_px=(
            estimate.quality.rms_error_px
            if isfinite(estimate.quality.rms_error_px) else None
        ),
        holdout_max_px=(
            estimate.quality.max_error_px
            if isfinite(estimate.quality.max_error_px) else None
        ),
    )
