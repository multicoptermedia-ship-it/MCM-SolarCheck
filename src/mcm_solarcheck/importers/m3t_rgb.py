"""Importer for DJI M3T visible-light ``*_V.JPG`` frames."""

from __future__ import annotations

from pathlib import Path
import re

from mcm_solarcheck.domain.models import ImageFrame
from .m3t_xmp import parse_m3t_xmp

_SEQ_RE = re.compile(r"_(\d{4})_V\.JPG$", re.IGNORECASE)


def _jpeg_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Read JPEG SOF dimensions without decoding image pixels."""
    if not data.startswith(b"\xff\xd8"):
        return None, None
    offset = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while offset + 4 <= len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        length = int.from_bytes(data[offset:offset + 2], "big")
        if length < 2 or offset + length > len(data):
            break
        if marker in sof and length >= 7:
            height = int.from_bytes(data[offset + 3:offset + 5], "big")
            width = int.from_bytes(data[offset + 5:offset + 7], "big")
            return width, height
        offset += length
    return None, None


class M3TRGBImporter:
    @staticmethod
    def frame_id(path: Path) -> str:
        match = _SEQ_RE.search(path.name)
        return f"V-{match.group(1)}" if match else f"V-{path.stem}"

    def import_file(self, path: str | Path) -> ImageFrame:
        source = Path(path)
        data = source.read_bytes()
        xmp = parse_m3t_xmp(data)
        width, height = _jpeg_dimensions(data)
        return ImageFrame(
            frame_id=self.frame_id(source), source_file=source,
            camera_make=xmp.camera_make, camera_model=xmp.camera_model,
            width=width, height=height, timestamp_utc=xmp.timestamp_utc,
            position=xmp.position, camera_pose=xmp.camera_pose,
            flight_pose=xmp.flight_pose, rtk=xmp.rtk, metadata=dict(xmp.raw),
        )

    def import_directory(self, directory: str | Path) -> tuple[ImageFrame, ...]:
        return tuple(self.import_file(path) for path in sorted(Path(directory).glob("*_V.JPG")))
