"""Read-only per-frame verification of imported DJI M3T 16-bit raw raster streams.

This is a technical *processing prerequisite*, NOT radiometric temperature
calibration, PV module segmentation, anomaly diagnosis, or human approval.
Only counts leave this module; private paths and customer bytes remain local.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Callable

from mcm_solarcheck.services.offline_processing_inventory import (
    capture_offline_processing_inventory,
)
from mcm_solarcheck.thermal.m3t_radiometric import M3TRadiometricParser

MAX_RAW_FILE_BYTES = 120_000_000


class ThermalRawCheckCancelled(Exception):
    """An operator aborted the read-only thermal-raster inspection."""


@dataclass(frozen=True)
class ThermalRawCheckResult:
    total: int
    checked: int
    valid_rasters: int
    checksum_verified: int
    without_checksum: int
    issues: int
    changed_inputs: bool
    read_only: bool = True

    @property
    def ready_for_later_analysis(self) -> bool:
        """File-level readiness only; NEVER an offline processing completion."""
        return (
            self.total > 0 and self.checked == self.total
            and self.valid_rasters == self.checksum_verified == self.total
            and self.without_checksum == self.issues == 0
            and not self.changed_inputs
        )


def _thermal_entries(database, project_id: str):
    """Return only the selected project's thermal frame references."""
    with database.connect() as sql:
        return tuple(sql.execute(
            "SELECT f.source_file,f.width,f.height,t.content_sha256 "
            "FROM thermal_frames AS f LEFT JOIN training_samples AS t "
            "ON t.project_id=f.project_id AND t.source_frame_id=f.frame_id "
            "AND t.modality='thermal' "
            "WHERE f.project_id=? ORDER BY f.frame_id",
            (project_id,),
        ).fetchall())


def _inspect_raw(
    source_path: str, width: int | None, height: int | None,
    expected_hash: str | None, *,
    parser: M3TRadiometricParser, should_cancel: Callable[[], bool],
    maximum_bytes: int,
) -> tuple[bool, bool]:
    """Validate raw raster + original import digest; never persist decoded samples."""
    path = Path(source_path)
    if path.is_symlink() or not path.is_file():
        return False, False
    try:
        before = path.stat()
        if before.st_size <= 0 or before.st_size > maximum_bytes:
            return False, False
        digest = sha256()
        parts = []
        size = 0
        with path.open("rb") as stream:
            while True:
                if should_cancel():
                    raise ThermalRawCheckCancelled()
                chunk = stream.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > maximum_bytes:
                    return False, False
                parts.append(chunk)
                digest.update(chunk)
        if size != before.st_size:
            return False, False
        if should_cancel():
            raise ThermalRawCheckCancelled()
        raster = parser.parse_bytes(b"".join(parts))
        # A valid APP3 stream must also match its imported SQLite dimensions.
        if raster.pixel_count != 640 * 512 or raster.byte_order != "little":
            return False, False
        if (width is not None and width != raster.width) or (
            height is not None and height != raster.height
        ):
            return False, False
        if should_cancel():
            raise ThermalRawCheckCancelled()
        after = path.stat()
        if (
            after.st_size != before.st_size or
            after.st_mtime_ns != before.st_mtime_ns or
            after.st_ino != before.st_ino
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
        verified = digest.hexdigest() == expected_hash.lower()
        return verified, verified
    except ThermalRawCheckCancelled:
        raise
    except (OSError, ValueError, TypeError):
        return False, False


def check_imported_thermal_raw(
    database, project_id: str, *, on_progress=None, should_cancel=None,
    maximum_bytes: int = MAX_RAW_FILE_BYTES,
) -> ThermalRawCheckResult:
    """Decode each imported 16-bit raster read-only with explicit failure counts.

    No SQLite mutation, no full image processing, and no workflow unlock.
    """
    if type(maximum_bytes) is not int or maximum_bytes < 1:
        raise ValueError("positive byte bound required")
    cancelled = should_cancel or (lambda: False)
    if cancelled():
        raise ThermalRawCheckCancelled()
    before = capture_offline_processing_inventory(database, project_id)
    entries = _thermal_entries(database, project_id)
    if before.thermal_frames != len(entries):
        raise ValueError("imported thermal inventory changed during inspection")
    parser = M3TRadiometricParser()
    valid = verified = unchecked = issues = 0
    for index, (source, width, height, expected_hash) in enumerate(entries, 1):
        if cancelled():
            raise ThermalRawCheckCancelled()
        ok, hash_ok = _inspect_raw(
            source, width, height, expected_hash,
            parser=parser, should_cancel=cancelled,
            maximum_bytes=maximum_bytes,
        )
        if ok:
            valid += 1
            if hash_ok:
                verified += 1
            else:
                unchecked += 1
        else:
            issues += 1
        if on_progress is not None:
            on_progress(index, len(entries), issues)
    if cancelled():
        raise ThermalRawCheckCancelled()
    after = capture_offline_processing_inventory(database, project_id)
    return ThermalRawCheckResult(
        total=len(entries), checked=len(entries), valid_rasters=valid,
        checksum_verified=verified, without_checksum=unchecked,
        issues=issues, changed_inputs=before.fingerprint != after.fingerprint,
    )
