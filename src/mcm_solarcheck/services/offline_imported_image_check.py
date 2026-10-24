"""Read-only, cancellable inspection of SQLite-imported image originals.

No exports, diagnosis, report approval, network traffic, or mutation of source
images. PIL.verify checks image structure, NOT full pixel/radiometric validity.
Names, customer paths, image bytes and coordinates never leave this service.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable

from PIL import Image, UnidentifiedImageError

from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)

MAX_INSPECTION_BYTES = 120_000_000


class ImportedImageCheckCancelled(Exception):
    """The user explicitly stopped the scan before it completed."""


@dataclass(frozen=True)
class ImportedImageCheckResult:
    total: int
    checked: int
    valid_images: int
    checksum_verified: int
    without_checksum: int
    issues: int
    changed_inputs: bool
    read_only: bool = True

    @property
    def safe_to_process(self) -> bool:
        # A file with no trusted checksum is not proven to match its import.
        return (
            self.total > 0 and self.checked == self.total and
            self.issues == 0 and self.without_checksum == 0
            and self.checksum_verified == self.total and
            not self.changed_inputs
        )


def _entries(database, project_id: str):
    """Return private source references, never UI-serializable status data."""
    with database.connect() as sql:
        rows = []
        for table, modality in (("image_frames", "rgb"), ("thermal_frames", "thermal")):
            rows.extend(sql.execute(
                f"SELECT f.frame_id, f.source_file, t.content_sha256 "
                f"FROM {table} AS f LEFT JOIN training_samples AS t "
                "ON t.project_id=f.project_id AND t.source_frame_id=f.frame_id "
                "AND t.modality=? WHERE f.project_id=? ORDER BY f.frame_id",
                (modality, project_id),
            ).fetchall())
    return tuple((r[1], r[2]) for r in rows)


def _inspect_one(
    source_path: str, expected_hash: str | None, *, should_cancel: Callable[[], bool],
    maximum_bytes: int,
) -> tuple[bool, bool]:
    """Return (structure_valid, verified_checksum), suppress path-bearing errors."""
    file = Path(source_path)
    if file.is_symlink() or not file.is_file():
        return False, False
    try:
        initial = file.stat()
        if initial.st_size <= 0 or initial.st_size > maximum_bytes:
            return False, False
        digest = sha256()
        consumed = 0
        with file.open("rb") as handle:
            while True:
                if should_cancel():
                    raise ImportedImageCheckCancelled()
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                consumed += len(chunk)
                if consumed > maximum_bytes:
                    return False, False
                digest.update(chunk)
        if consumed != initial.st_size:
            return False, False
        with Image.open(file) as decoded:
            if decoded.format not in ("JPEG", "PNG", "TIFF"):
                return False, False
            decoded.verify()
        final = file.stat()
        if (
            final.st_size != initial.st_size or
            final.st_mtime_ns != initial.st_mtime_ns or
            final.st_ino != initial.st_ino
        ):
            return False, False
        if expected_hash is None:
            return True, False
        if (
            not isinstance(expected_hash, str)
            or len(expected_hash) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in expected_hash)
        ):
            return False, False
        matched = digest.hexdigest() == expected_hash.lower()
        return matched, matched
    except ImportedImageCheckCancelled:
        raise
    except (OSError, ValueError, SyntaxError, UnidentifiedImageError):
        return False, False


def check_imported_image_originals(
    database, project_id: str, *, on_progress=None, should_cancel=None,
    maximum_bytes: int = MAX_INSPECTION_BYTES,
) -> ImportedImageCheckResult:
    """Check each imported RGB/thermal file without modifying DB or originals.

    Positive result still proves neither a complete image analysis nor any
    radiometric temperature/geometric registration; never unlocks review.
    """
    if type(maximum_bytes) is not int or maximum_bytes < 1:
        raise ValueError("positive byte bound required")
    cancelled = should_cancel or (lambda: False)
    if cancelled():
        raise ImportedImageCheckCancelled()
    before = capture_offline_processing_inventory(database, project_id)
    entries = _entries(database, project_id)
    total = before.rgb_frames + before.thermal_frames
    if total != len(entries):
        raise ValueError("imported inventory changed during inspection")
    valid = verified = unchecked = issues = 0
    for index, (source, expected_hash) in enumerate(entries, 1):
        if cancelled():
            raise ImportedImageCheckCancelled()
        structure, matched = _inspect_one(
            source, expected_hash, should_cancel=cancelled,
            maximum_bytes=maximum_bytes,
        )
        if structure:
            valid += 1
            if matched:
                verified += 1
            else:
                unchecked += 1
        else:
            issues += 1
        if on_progress is not None:
            on_progress(index, total, issues)
    if cancelled():
        raise ImportedImageCheckCancelled()
    after = capture_offline_processing_inventory(database, project_id)
    return ImportedImageCheckResult(
        total=total, checked=total, valid_images=valid,
        checksum_verified=verified, without_checksum=unchecked,
        issues=issues, changed_inputs=before.fingerprint != after.fingerprint,
    )
