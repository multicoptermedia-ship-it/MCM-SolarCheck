"""Read multiple real DJI M3T RGB ZIP archives as ONE private flight series.

ZIP member bytes are decoded transiently for DJI XMP / original sensor size.
No archive extraction, rewriting, network, customer GPS report or SQLite work.
An uploaded archive named .tip is allowed when ZIP bytes are valid: the suffix
does not define the format.

This is a source intake for future whole-flight SfM, NOT an orthophoto.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path, PurePosixPath
import re
import stat
from zipfile import ZipFile, BadZipFile

from mcm_solarcheck.importers.m3t_rgb import _jpeg_dimensions
from mcm_solarcheck.importers.m3t_xmp import parse_m3t_xmp
from mcm_solarcheck.domain.models import Pose, Position, RTKQuality

_NAME = re.compile(r"DJI_(\d{14})_(\d{4})_V\.JPG\Z",re.IGNORECASE)


@dataclass(frozen=True)
class PrivateRGBFlightFrame:
    """Private, in-memory flight data; DO NOT persist to a public report."""

    source_archive: Path
    member_name: str
    frame_id: str
    capture_stamp: str
    width: int
    height: int
    position: Position | None
    camera_pose: Pose
    flight_pose: Pose
    rtk: RTKQuality
    xmp_keys: tuple[str, ...]
    image_size_bytes: int


@dataclass(frozen=True)
class PrivateRGBFlightSeries:
    frames: tuple[PrivateRGBFlightFrame, ...]
    archives_read: int
    discarded_non_rgb_members: int

    def privacy_safe_summary(self) -> dict:
        """No GPS values, timestamps, filenames, archive paths or raw XMP."""
        rtk = [f.rtk for f in self.frames]
        return {
            "schema":"mcm.private_multi_rgb_zip_intake.v1",
            "status":"rgb_exif_xmp_inventory_not_an_orthophoto",
            "archive_count":self.archives_read,
            "unique_rgb_frames":len(self.frames),
            "discarded_non_rgb_entries":self.discarded_non_rgb_members,
            "primary_4000x3000_frames":sum(
                (x.width,x.height)==(4000,3000) for x in self.frames
            ),
            "frames_with_gnss_coordinates":sum(f.position is not None for f in self.frames),
            "frames_with_gnss_altitude":sum(
                f.position is not None and f.position.altitude_m is not None
                for f in self.frames
            ),
            "frames_with_complete_gimbal_angles":sum(
                all(x is not None for x in (
                    f.camera_pose.yaw_deg,f.camera_pose.pitch_deg,f.camera_pose.roll_deg
                )) for f in self.frames
            ),
            "frames_with_complete_flight_angles":sum(
                all(x is not None for x in (
                    f.flight_pose.yaw_deg,f.flight_pose.pitch_deg,f.flight_pose.roll_deg
                )) for f in self.frames
            ),
            "frames_with_rtk_status":sum(x.status is not None for x in rtk),
            "frames_with_rtk_standard_deviations":sum(
                x.std_lat_m is not None and x.std_lon_m is not None
                and x.std_height_m is not None for x in rtk
            ),
            "frames_with_dewarp_metadata":sum(
                any(key.lower().startswith("dewarp") for key in f.xmp_keys)
                for f in self.frames
            ),
            "frame_geolocation_values_in_report":False,
            "complete_flight_coverage_verified":False,
            "image_overlap_verified":False,
            "photogrammetric_3d_verified":False,
            "rgb_orthophoto_created":False,
        }


def read_private_rgb_zip_series(
    archives: tuple[str | Path, ...],
    *,
    max_archives: int = 32,
    max_images: int = 1000,
    max_member_bytes: int = 40_000_000,
    max_archive_bytes: int = 10_000_000_000,
    should_cancel=None,
    on_progress=None,
) -> PrivateRGBFlightSeries:
    """Index the exact available ZIP RGB frames; no filename-only claims.

    ZIP filename suffix can be anything; contents must be a real valid ZIP.
    Nested directories are accepted when safe, but duplicate frame identities
    across ZIPs are always rejected instead of silently merging/replacing.
    """
    def cancel():
        if should_cancel is not None and should_cancel():
            raise RuntimeError("multi-ZIP RGB intake cancelled")
    cancel()
    if (type(archives) is not tuple or not 1<=len(archives)<=max_archives<=64
            or type(max_images) is not int or not 1<=max_images<=3000
            or type(max_member_bytes) is not int or not 128<=max_member_bytes<=60_000_000
            or type(max_archive_bytes) is not int or not 1024<=max_archive_bytes<=35_000_000_000):
        raise ValueError("bounded DJI RGB archive intake required")
    sources = [Path(x) for x in archives]
    if (any(not p.is_file() or p.is_symlink() for p in sources)
            or len({p.resolve() for p in sources}) != len(sources)):
        raise ValueError("unique existing regular RGB ZIP files required")
    result: dict[tuple[str,str],PrivateRGBFlightFrame] = {}
    ignored = 0
    for archive_index,path in enumerate(sources):
        cancel()
        try:
            with ZipFile(path,"r") as zf:
                entries = zf.infolist()
                if not 1<=len(entries)<=15000 or sum(x.file_size for x in entries)>max_archive_bytes:
                    raise ValueError("RGB ZIP directory exceeds bounded intake")
                for entry in entries:
                    cancel()
                    parts=PurePosixPath(entry.filename)
                    if (parts.is_absolute() or ".." in parts.parts
                            or "\\" in entry.filename or
                            re.match(r"^[A-Za-z]:",entry.filename)):
                        raise ValueError("unsafe member path in private RGB ZIP")
                    if entry.is_dir():
                        continue
                    typ=stat.S_IFMT(entry.external_attr>>16)
                    if typ not in (0,stat.S_IFREG):
                        raise ValueError("nonregular ZIP member disallowed")
                    match=_NAME.fullmatch(parts.name)
                    if match is None:
                        ignored+=1
                        continue
                    if not 128<=entry.file_size<=max_member_bytes:
                        raise ValueError("DJI RGB original exceeds bounded file size")
                    if len(result)>=max_images:
                        raise ValueError("whole-flight RGB image budget exceeded")
                    stamp,counter=match.groups()
                    identity=(stamp,counter)
                    if identity in result:
                        raise ValueError("duplicate original DJI RGB flight frame")
                    # No ZIP member is ever written to disk. Limit decompressed
                    # bytes even if the ZIP header claims a smaller size.
                    with zf.open(entry) as fp:
                        payload=fp.read(max_member_bytes+1)
                    if len(payload)!=entry.file_size or len(payload)>max_member_bytes:
                        raise ValueError("truncated or oversized DJI RGB photo")
                    try:
                        xmp=parse_m3t_xmp(payload)
                        width,height=_jpeg_dimensions(payload)
                    except (TypeError,ValueError) as error:
                        raise ValueError("unreadable DJI RGB XMP metadata") from error
                    if (width is None or height is None or not 256<=width<=10000
                            or not 256<=height<=10000):
                        raise ValueError("missing real primary RGB JPEG sensor dimensions")
                    position=xmp.position
                    if position is not None:
                        values=(position.latitude,position.longitude)
                        if (not all(isfinite(v) for v in values)
                                or not -90<=position.latitude<=90
                                or not -180<=position.longitude<=180):
                            raise ValueError("invalid DJI GNSS position")
                        if position.altitude_m is not None and not isfinite(position.altitude_m):
                            raise ValueError("invalid DJI GNSS altitude")
                    for angle in (
                        xmp.camera_pose.yaw_deg,xmp.camera_pose.pitch_deg,
                        xmp.camera_pose.roll_deg,xmp.flight_pose.yaw_deg,
                        xmp.flight_pose.pitch_deg,xmp.flight_pose.roll_deg,
                    ):
                        if angle is not None and not isfinite(angle):
                            raise ValueError("nonfinite DJI camera or flight angle")
                    for std in (
                        xmp.rtk.std_lat_m,xmp.rtk.std_lon_m,xmp.rtk.std_height_m,
                    ):
                        if std is not None and (not isfinite(std) or std<0):
                            raise ValueError("invalid DJI RTK uncertainty")
                    result[identity]=PrivateRGBFlightFrame(
                        path,entry.filename,f"V-{counter}",stamp,width,height,
                        position,xmp.camera_pose,xmp.flight_pose,xmp.rtk,
                        tuple(sorted(xmp.raw)),entry.file_size,
                    )
                    if on_progress is not None:
                        on_progress(len(result))
        except BadZipFile as error:
            raise ValueError("invalid RGB ZIP bytes (extension is irrelevant)") from error
        if not result:
            raise ValueError("no supported DJI RGB photographs found")
    # Two exposure timestamps with reused 4-digit counter are ambiguous for
    # a legacy SolarCheck project ID: reject rather than silently conflating.
    counters=[x.frame_id for x in result.values()]
    if len(counters)!=len(set(counters)):
        raise ValueError("reused DJI sequence counter across flight archives")
    ordered=tuple(result[x] for x in sorted(result))
    return PrivateRGBFlightSeries(ordered,len(sources),ignored)
