"""Explicit, read-only local RGB/thermal JPEG preview for expert review.

The stored source path is evidence of a filename only. It is NEVER opened:
the user must select a local directory, with no symlink traversal. These are
RGB renderings of JPEG/PNG bytes, not radiometric temperature measurements or
proof that a filename identifies an unchanged original flight image.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from math import isfinite
import os
from pathlib import Path
import re
import stat

from PIL import Image, ImageDraw, ImageOps

from mcm_solarcheck.storage.sqlite import ProjectDatabase

MAX_IMAGE_BYTES = 40 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
PREVIEW_SIZE = (640, 420)


@dataclass(frozen=True)
class ReviewImageEvidence:
    """Memory-only previews and the outcome of optional import-time SHA-256 checks."""
    thermal_png: bytes | None
    rgb_png: bytes | None
    thermal_integrity: str
    rgb_integrity: str
    thermal_marker: str = "unavailable"
    rgb_marker: str = "unavailable"


def _name_from_stored_source(source: str | None) -> str | None:
    if not isinstance(source, str) or not source or "\x00" in source:
        return None
    # Windows originals can be inspected on a Linux development machine too.
    name = source.replace("\\", "/").rsplit("/", 1)[-1]
    if (
        name in ("", ".", "..") or ":" in name
        or len(name) > 255 or Path(name).suffix.lower() not in (".jpg", ".jpeg", ".png")
    ):
        return None
    return name


def _safe_selected_directory(directory: str | Path) -> Path:
    root = Path(directory)
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("select an existing absolute local flight folder")
    # No UNC network shares, junctions or symlink ancestors.
    if str(root).startswith(("\\\\", "//")):
        raise ValueError("network folders not supported")
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise ValueError("flight folder must not contain symbolic links")
    return root


def _render_thumbnail(
    root: Path, stored_source: str | None, expected_sha256: str | None,
    *, expected_size: tuple[int | None, int | None],
    marker_position: tuple[float | int | None, float | int | None] | None,
    mapping_validated: bool,
) -> tuple[bytes | None, str, str]:
    name = _name_from_stored_source(stored_source)
    if name is None:
        return None, "unavailable", "unavailable"
    path = root / name
    if path.is_symlink():
        raise ValueError("image links are not allowed")
    try:
        details = path.stat()
    except FileNotFoundError:
        return None, "unavailable", "unavailable"
    if not stat.S_ISREG(details.st_mode) or details.st_size > MAX_IMAGE_BYTES:
        raise ValueError("unsupported image file")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        with os.fdopen(fd, "rb") as stream:
            fd = -1
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode) or (
                os.fstat(stream.fileno()).st_size > MAX_IMAGE_BYTES
            ):
                raise ValueError("unsupported image file")
            if expected_sha256 is not None:
                # A corrupt stored digest is not proof of an image. Do not
                # show the same-name replacement in that case.
                if not isinstance(expected_sha256, str) or not re.fullmatch(
                    r"[0-9a-fA-F]{64}", expected_sha256,
                ):
                    return None, "mismatch", "unavailable"
                digest = sha256()
                scanned = 0
                while chunk := stream.read(1024 * 1024):
                    scanned += len(chunk)
                    if scanned > MAX_IMAGE_BYTES:
                        raise ValueError("image exceeded local byte limit")
                    digest.update(chunk)
                if digest.hexdigest() != expected_sha256.lower():
                    return None, "mismatch", "unavailable"
                stream.seek(0)
                integrity = "verified"
            else:
                integrity = "unverified"
            with Image.open(stream) as img:
                if (
                    img.format not in ("JPEG", "PNG")
                    or img.width < 1 or img.height < 1
                    or img.width * img.height > MAX_IMAGE_PIXELS
                ):
                    raise ValueError("unsupported image format or dimensions")
                # Persisted thermal pixel coordinates are NOT automatically
                # the JPEG display coordinates. Only matching native dimensions
                # and unrotated orientation permit a conservative locator.
                raw_width, raw_height = img.size
                orientation = img.getexif().get(274, 1)
                img.thumbnail(PREVIEW_SIZE)
                thumbnail = ImageOps.exif_transpose(img).convert("RGB")
                if not mapping_validated:
                    marker = "unvalidated"
                elif (
                    type(expected_size[0]) is not int
                    or type(expected_size[1]) is not int
                    or expected_size != (raw_width, raw_height)
                ):
                    marker = "different_geometry"
                elif orientation != 1:
                    marker = "orientation"
                elif marker_position is None or any(
                    value is None or isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(float(value))
                    for value in marker_position
                ):
                    marker = "outside"
                else:
                    x, y = marker_position
                    if not (0 <= x < raw_width and 0 <= y < raw_height):
                        marker = "outside"
                    else:
                        cx = round((x + 0.5) * thumbnail.width / raw_width)
                        cy = round((y + 0.5) * thumbnail.height / raw_height)
                        # A plain sight-image locator, not a diagnostic overlay.
                        draw = ImageDraw.Draw(thumbnail)
                        radius = 8
                        draw.ellipse(
                            (cx-radius-1, cy-radius-1, cx+radius+1, cy+radius+1),
                            outline="#101a28", width=4,
                        )
                        draw.ellipse(
                            (cx-radius, cy-radius, cx+radius, cy+radius),
                            outline="#39f3bd", width=2,
                        )
                        draw.line(
                            (cx-12, cy, cx+12, cy), fill="#39f3bd", width=2,
                        )
                        draw.line(
                            (cx, cy-12, cx, cy+12), fill="#39f3bd", width=2,
                        )
                        marker = "marked"
                payload = BytesIO()
                thumbnail.save(payload, format="PNG")
                return payload.getvalue(), integrity, marker
    finally:
        if fd >= 0:
            os.close(fd)


def preview_pending_finding_image_evidence(
    database: ProjectDatabase, project_id: str, finding_id: str,
    selected_folder: str | Path,
) -> ReviewImageEvidence:
    """Return read-only previews and their per-frame import hash-check statuses.

    An unreviewed candidate is read via project-qualified foreign keys. The
    selected folder is unrelated to persisted absolute source paths except for
    basename matching; no scanning, recursion, upload or filesystem mutation.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("active project required")
    if not isinstance(finding_id, str) or not finding_id.strip():
        raise ValueError("stored finding required")
    with database.connect() as db:
        row = db.execute(
            """
            SELECT t.source_file AS thermal_source,
                   r.source_file AS rgb_source,
                   t.width AS thermal_width, t.height AS thermal_height,
                   f.pixel_x AS thermal_x, f.pixel_y AS thermal_y,
                   r.width AS rgb_width, r.height AS rgb_height,
                   l.rgb_pixel_x AS rgb_x, l.rgb_pixel_y AS rgb_y,
                   l.transform_validated AS rgb_transform_validated,
                   (SELECT ts.content_sha256 FROM training_samples AS ts
                     WHERE ts.project_id=f.project_id
                       AND ts.source_frame_id=t.frame_id
                       AND ts.modality='thermal') AS thermal_sha256,
                   (SELECT rs.content_sha256 FROM training_samples AS rs
                     WHERE rs.project_id=f.project_id
                       AND rs.source_frame_id=r.frame_id
                       AND rs.modality='rgb') AS rgb_sha256
              FROM findings AS f
              JOIN thermal_frames AS t
                ON t.project_id=f.project_id
               AND t.frame_id=f.thermal_frame_id
              LEFT JOIN finding_sensor_links AS l
                ON l.project_id=f.project_id
               AND l.finding_id=f.finding_id
              LEFT JOIN image_frames AS r
                ON r.project_id=f.project_id
               AND r.frame_id=l.rgb_frame_id
             WHERE f.project_id=? AND f.finding_id=?
               AND f.reviewer_status='unreviewed'
            """, (project_id, finding_id),
        ).fetchone()
    if row is None:
        raise ValueError("finding is not pending in the active project")
    root = _safe_selected_directory(selected_folder)
    thermal_name = _name_from_stored_source(row["thermal_source"])
    rgb_name = _name_from_stored_source(row["rgb_source"])
    if thermal_name and rgb_name and thermal_name.casefold() == rgb_name.casefold():
        raise ValueError("ambiguous thermal/RGB filenames")
    thermal, thermal_integrity, thermal_marker = _render_thumbnail(
        root, row["thermal_source"], row["thermal_sha256"],
        expected_size=(row["thermal_width"], row["thermal_height"]),
        marker_position=(row["thermal_x"], row["thermal_y"]),
        mapping_validated=True,
    )
    rgb, rgb_integrity, rgb_marker = _render_thumbnail(
        root, row["rgb_source"], row["rgb_sha256"],
        expected_size=(row["rgb_width"], row["rgb_height"]),
        marker_position=(row["rgb_x"], row["rgb_y"]),
        mapping_validated=row["rgb_transform_validated"] == 1,
    )
    return ReviewImageEvidence(
        thermal, rgb, thermal_integrity, rgb_integrity,
        thermal_marker, rgb_marker,
    )


def preview_pending_finding_images(
    database: ProjectDatabase, project_id: str, finding_id: str,
    selected_folder: str | Path,
) -> tuple[bytes | None, bytes | None]:
    """Backwards-compatible thumbnail API; checks any stored image hashes."""
    evidence = preview_pending_finding_image_evidence(
        database, project_id, finding_id, selected_folder,
    )
    return evidence.thermal_png, evidence.rgb_png
