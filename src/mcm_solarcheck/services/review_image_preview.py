"""Explicit, read-only local RGB/thermal JPEG preview for expert review.

The stored source path is evidence of a filename only. It is NEVER opened:
the user must select a local directory, with no symlink traversal. These are
RGB renderings of JPEG/PNG bytes, not radiometric temperature measurements or
proof that a filename identifies an unchanged original flight image.
"""
from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import stat

from PIL import Image, ImageOps

from mcm_solarcheck.storage.sqlite import ProjectDatabase

MAX_IMAGE_BYTES = 40 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
PREVIEW_SIZE = (640, 420)


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


def _render_thumbnail(root: Path, stored_source: str | None) -> bytes | None:
    name = _name_from_stored_source(stored_source)
    if name is None:
        return None
    path = root / name
    if path.is_symlink():
        raise ValueError("image links are not allowed")
    try:
        details = path.stat()
    except FileNotFoundError:
        return None
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
            with Image.open(stream) as img:
                if (
                    img.format not in ("JPEG", "PNG")
                    or img.width < 1 or img.height < 1
                    or img.width * img.height > MAX_IMAGE_PIXELS
                ):
                    raise ValueError("unsupported image format or dimensions")
                # Decode only once, reduce size before expensive RGB expansion.
                img.thumbnail(PREVIEW_SIZE)
                thumbnail = ImageOps.exif_transpose(img).convert("RGB")
                payload = BytesIO()
                thumbnail.save(payload, format="PNG")
                return payload.getvalue()
    finally:
        if fd >= 0:
            os.close(fd)


def preview_pending_finding_images(
    database: ProjectDatabase, project_id: str, finding_id: str,
    selected_folder: str | Path,
) -> tuple[bytes | None, bytes | None]:
    """Return (thermal PNG thumbnail, linked RGB PNG thumbnail).

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
                   r.source_file AS rgb_source
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
    return (
        _render_thumbnail(root, row["thermal_source"]),
        _render_thumbnail(root, row["rgb_source"]),
    )
