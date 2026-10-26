"""One narrow offline RGB vertical slice: selected project -> originals -> PNG.

Only an UNVERIFIED, nonmetric two-frame visual diagnostic is produced.
No camera/roof geometry, module identification, RTK accuracy, thermal values,
database migration, or expert approval may be inferred from this preview.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3

import cv2
from PIL import Image

from mcm_solarcheck.services.orthomosaic_rgb_stitch_preview import (
    save_rgb_preview_artifacts,
    stitch_rgb_preview,
)

_RGB_NAME = re.compile(r"DJI_\d{14}_(\d{4})_V\.JPG\Z", re.IGNORECASE)


@dataclass(frozen=True)
class ProjectRGBPreviewResult:
    png_path: Path
    manifest_path: Path
    first_sequence: str
    second_sequence: str
    inliers: int
    canvas_covered_fraction: float
    median_reprojection_error_px: float | None
    status: str = "unverified_nonmetric_rgb_preview"
    metric_orthophoto_verified: bool = False


def _selected_rgb_paths(
    database: Path, project_id: str, first: str, second: str,
    *, max_file_bytes: int,
) -> tuple[Path, Path]:
    """Read frame names from a SQLite file opened strictly read-only."""
    if not database.is_file() or database.is_symlink():
        raise ValueError("existing regular local test database required")
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("nonempty project ID required")
    if (not isinstance(first, str) or not isinstance(second, str)
            or re.fullmatch(r"\d{4}", first) is None
            or re.fullmatch(r"\d{4}", second) is None
            or int(second) != int(first) + 1):
        raise ValueError("two consecutive four-digit RGB capture numbers required")
    if type(max_file_bytes) is not int or max_file_bytes < 1:
        raise ValueError("positive image byte limit required")

    uri = database.resolve(strict=True).as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute(
            "SELECT 1 FROM projects WHERE project_id=?", (project_id,),
        ).fetchone() is None:
            raise ValueError("selected project does not exist")
        rows = db.execute(
            "SELECT source_file, width, height FROM image_frames "
            "WHERE project_id=? ORDER BY timestamp_utc, frame_id",
            (project_id,),
        ).fetchall()

    selected: dict[str, tuple[Path, int, int]] = {}
    for filename, width, height in rows:
        if not isinstance(filename, str):
            continue
        match = _RGB_NAME.fullmatch(Path(filename).name)
        if match is None or match.group(1) not in (first, second):
            continue
        identifier = match.group(1)
        if identifier in selected:
            raise ValueError("ambiguous duplicate DJI RGB capture number")
        path = Path(filename)
        if not path.is_absolute():
            path = database.parent / path
        selected[identifier] = (path, width, height)

    if set(selected) != {first, second}:
        raise ValueError("requested consecutive RGB frames are not imported")
    result = []
    for number in (first, second):
        path, width, height = selected[number]
        if not path.is_file() or path.is_symlink():
            raise ValueError("imported original RGB image must be a regular file")
        if path.stat().st_size > max_file_bytes:
            raise ValueError("imported RGB image exceeds byte limit")
        if type(width) is not int or type(height) is not int or width < 128 or height < 128:
            raise ValueError("imported RGB image dimensions missing or invalid")
        with Image.open(path) as image:
            if image.format not in ("JPEG", "MPO"):
                raise ValueError("DJI RGB source must be JPEG or MPO")
            # The sensor-size primary RGB frame is MPO frame 0; never select
            # the small 960x720 companion as if it were original RGB detail.
            image.seek(0)
            if image.size != (width, height):
                raise ValueError("MPO/JPEG primary frame dimensions do not match import")
            if image.mode not in ("RGB", "L"):
                raise ValueError("unsupported primary RGB format")
        reduced = cv2.imread(str(path), cv2.IMREAD_REDUCED_COLOR_4)
        if reduced is None or reduced.shape[:2] != (height // 4, width // 4):
            raise ValueError("OpenCV did not decode the expected primary DJI RGB frame")
        result.append(path)
    return result[0], result[1]


def create_project_rgb_preview(
    database: str | Path,
    project_id: str,
    first_sequence: str,
    second_sequence: str,
    output_directory: str | Path,
    *,
    max_file_bytes: int = 80_000_000,
    max_side: int = 1400,
    max_canvas_pixels: int = 12_000_000,
) -> ProjectRGBPreviewResult:
    """Render one selected consecutive RGB pair to a new, empty local folder.

    Preview files are the ONLY possible writes. The project database is opened
    with SQLite mode=ro and the original source files are never changed.
    """
    db = Path(database)
    directory = Path(output_directory)
    if (
        not directory.is_dir() or directory.is_symlink()
        or any(directory.iterdir())
    ):
        raise ValueError("existing empty regular output directory required")
    if not 128 <= max_side <= 1400 or not 100_000 <= max_canvas_pixels <= 12_000_000:
        raise ValueError("bounded RGB preview resolution and pixel budget required")

    first, second = _selected_rgb_paths(
        db, project_id, first_sequence, second_sequence,
        max_file_bytes=max_file_bytes,
    )
    target = directory.resolve(strict=True)
    for source in (first, second, db):
        source_resolved = source.resolve(strict=True)
        if target == source_resolved.parent or target == source_resolved:
            raise ValueError("preview output cannot share original source directory")
        if target in source_resolved.parents:
            raise ValueError("preview cannot be written above original source files")
    # Fail if this new output folder is INSIDE an original-photo folder.
    if any(source.resolve(strict=True).parent in target.parents for source in (first, second)):
        raise ValueError("preview folder cannot be inside original-photo directory")

    preview = stitch_rgb_preview(
        first, second, max_side=max_side,
        max_canvas_pixels=max_canvas_pixels,
    )
    png, manifest = save_rgb_preview_artifacts(
        preview, target, source_names=(first.name, second.name),
    )
    return ProjectRGBPreviewResult(
        png, manifest, first_sequence, second_sequence, preview.inliers,
        preview.covered_fraction, preview.median_reprojection_error_px,
    )
