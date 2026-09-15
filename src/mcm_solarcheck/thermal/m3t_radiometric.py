"""Structural parser for DJI Mavic 3 Thermal radiometric JPEG/MPO files.

The M3T files validated by this project contain a DJI radiometric marker stream
between JPEG/MPO image data.  The stream begins with ten full APP3 payloads and
one final APP3 payload, followed by APP4/APP5 calibration/auxiliary data.

This module deliberately exposes raw 16-bit samples only. Celsius conversion
belongs behind an independently validated DJI/provider adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct

APP3 = 0xE3
APP4 = 0xE4
APP5 = 0xE5


@dataclass(frozen=True)
class JpegSegment:
    marker: int
    offset: int
    payload: bytes


@dataclass(frozen=True)
class RadiometricRaster:
    width: int
    height: int
    byte_order: str
    samples: tuple[int, ...]
    stream_offset: int

    @property
    def pixel_count(self) -> int:
        return self.width * self.height


class M3TFormatError(ValueError):
    """Raised when an input cannot be validated as the expected M3T layout."""


class M3TRadiometricParser:
    width = 640
    height = 512
    bytes_per_sample = 2
    full_app3_payload_size = 65532

    @property
    def expected_payload_size(self) -> int:
        return self.width * self.height * self.bytes_per_sample

    def parse_file(self, path: str | Path) -> RadiometricRaster:
        return self.parse_bytes(Path(path).read_bytes())

    def parse_bytes(self, data: bytes) -> RadiometricRaster:
        segments = self.radiometric_segments(data)
        payload = b"".join(s.payload for s in segments if s.marker == APP3)
        if len(payload) != self.expected_payload_size:
            raise M3TFormatError(
                f"Expected {self.expected_payload_size} radiometric APP3 bytes, "
                f"observed {len(payload)}"
            )
        samples = struct.unpack(f"<{self.width * self.height}H", payload)
        return RadiometricRaster(
            width=self.width,
            height=self.height,
            byte_order="little",
            samples=samples,
            stream_offset=segments[0].offset,
        )

    def auxiliary_blocks(self, data: bytes) -> dict[int, tuple[bytes, ...]]:
        result: dict[int, list[bytes]] = {APP4: [], APP5: []}
        for segment in self.radiometric_segments(data):
            if segment.marker in result:
                result[segment.marker].append(segment.payload)
        return {marker: tuple(parts) for marker, parts in result.items()}

    def radiometric_segments(self, data: bytes) -> tuple[JpegSegment, ...]:
        """Locate and parse the contiguous DJI radiometric APP marker stream.

        Searching every FF E3 byte is unsafe because the same byte sequence may
        occur inside JPEG entropy data or inside the raw thermal payload itself.
        We identify the stream by the first APP3 segment with DJI's full 65532
        byte payload and then advance strictly by each declared segment length.
        """
        signature = b"\xff\xe3\xff\xfe"  # APP3, length 65534 => payload 65532
        starts: list[int] = []
        pos = 0
        while True:
            pos = data.find(signature, pos)
            if pos < 0:
                break
            starts.append(pos)
            pos += 1

        candidates: list[tuple[JpegSegment, ...]] = []
        for start in starts:
            try:
                chain = self._parse_app_chain(data, start)
            except M3TFormatError:
                continue
            app3 = [s for s in chain if s.marker == APP3]
            raw_size = sum(len(s.payload) for s in app3)
            app4 = [s for s in chain if s.marker == APP4]
            app5 = [s for s in chain if s.marker == APP5]
            if raw_size == self.expected_payload_size and len(app4) == 1 and len(app4[0].payload) == 256 and len(app5) == 1 and len(app5[0].payload) == 23818:
                candidates.append(chain)

        if not candidates:
            raise M3TFormatError("No validated M3T radiometric APP stream found")
        # Later full-size APP3 blocks belong to the same chain; deduplicate by
        # accepting only the candidate with the earliest stream offset.
        candidates.sort(key=lambda c: c[0].offset)
        return candidates[0]

    @staticmethod
    def _parse_app_chain(data: bytes, start: int) -> tuple[JpegSegment, ...]:
        segments: list[JpegSegment] = []
        i = start
        n = len(data)
        while i + 4 <= n and data[i] == 0xFF and 0xE0 <= data[i + 1] <= 0xEF:
            marker = data[i + 1]
            length = int.from_bytes(data[i + 2:i + 4], "big")
            if length < 2:
                raise M3TFormatError(f"Invalid APP segment length {length}")
            end = i + 2 + length
            if end > n:
                raise M3TFormatError("APP segment extends beyond file")
            segments.append(JpegSegment(marker=marker, offset=i, payload=data[i + 4:end]))
            i = end
        return tuple(segments)
