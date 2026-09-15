"""Structural parser for DJI Mavic 3 Thermal radiometric JPEG/MPO files.

This module deliberately exposes *raw* 16-bit samples only.  It does not
claim that the values are temperatures.  Celsius conversion belongs behind
an independently validated DJI/provider adapter.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Iterable


SOI = 0xD8
EOI = 0xD9
SOS = 0xDA
APP3 = 0xE3
APP4 = 0xE4
APP5 = 0xE5


@dataclass(frozen=True)
class JpegSegment:
    marker: int
    offset: int
    payload: bytes
    component_index: int


@dataclass(frozen=True)
class RadiometricRaster:
    width: int
    height: int
    byte_order: str
    samples: tuple[int, ...]
    component_index: int

    @property
    def pixel_count(self) -> int:
        return self.width * self.height


class M3TFormatError(ValueError):
    """Raised when an input cannot be validated as the expected M3T layout."""


class M3TRadiometricParser:
    """Parse M3T JPEG/MPO structure without performing temperature conversion."""

    width = 640
    height = 512
    bytes_per_sample = 2

    @property
    def expected_payload_size(self) -> int:
        return self.width * self.height * self.bytes_per_sample

    def parse_file(self, path: str | Path) -> RadiometricRaster:
        return self.parse_bytes(Path(path).read_bytes())

    def parse_bytes(self, data: bytes) -> RadiometricRaster:
        segments = tuple(self.iter_segments(data))
        candidates: list[tuple[int, bytes]] = []

        # APP3 must be grouped per JPEG/MPO component.  Never concatenate APP3
        # globally: real M3T files can contain multiple JPEG components.
        component_ids = sorted({s.component_index for s in segments})
        for component_id in component_ids:
            payload = b"".join(
                s.payload
                for s in segments
                if s.component_index == component_id and s.marker == APP3
            )
            if len(payload) == self.expected_payload_size:
                candidates.append((component_id, payload))

        if not candidates:
            sizes = {
                cid: sum(
                    len(s.payload)
                    for s in segments
                    if s.component_index == cid and s.marker == APP3
                )
                for cid in component_ids
            }
            raise M3TFormatError(
                f"No component contains the expected {self.expected_payload_size} "
                f"APP3 bytes; observed={sizes}"
            )
        if len(candidates) > 1:
            raise M3TFormatError(
                f"Ambiguous radiometric payload: matching components "
                f"{[cid for cid, _ in candidates]}"
            )

        component_id, payload = candidates[0]
        # Byte order is currently an explicit structural assumption to be
        # validated against DJI reference output before temperatures are used.
        samples = struct.unpack(f"<{self.width * self.height}H", payload)
        return RadiometricRaster(
            width=self.width,
            height=self.height,
            byte_order="little",
            samples=samples,
            component_index=component_id,
        )

    def auxiliary_blocks(self, data: bytes, component_index: int) -> dict[int, tuple[bytes, ...]]:
        """Return un-interpreted APP4/APP5 payloads for later calibration research."""
        result: dict[int, list[bytes]] = {APP4: [], APP5: []}
        for segment in self.iter_segments(data):
            if segment.component_index == component_index and segment.marker in result:
                result[segment.marker].append(segment.payload)
        return {marker: tuple(parts) for marker, parts in result.items()}

    def iter_segments(self, data: bytes) -> Iterable[JpegSegment]:
        """Walk JPEG marker segments and keep MPO/JPEG components separate.

        Entropy-coded scan data is skipped safely, including byte stuffing and
        restart markers. A new SOI after EOI starts the next component.
        """
        i = 0
        component = -1
        in_scan = False
        n = len(data)

        while i + 1 < n:
            if data[i] != 0xFF:
                i += 1
                continue

            marker_offset = i
            while i < n and data[i] == 0xFF:
                i += 1
            if i >= n:
                break
            marker = data[i]
            i += 1

            if marker == 0x00:  # stuffed 0xFF inside entropy-coded data
                continue
            if 0xD0 <= marker <= 0xD7:  # restart marker
                continue
            if marker == SOI:
                component += 1
                in_scan = False
                continue
            if marker == EOI:
                in_scan = False
                continue

            # Standalone markers do not carry a length field.
            if marker == 0x01:
                continue

            if i + 2 > n:
                raise M3TFormatError("Truncated JPEG segment length")
            length = int.from_bytes(data[i:i + 2], "big")
            if length < 2:
                raise M3TFormatError(f"Invalid JPEG segment length {length}")
            end = i + length
            if end > n:
                raise M3TFormatError("JPEG segment extends beyond file")
            payload = data[i + 2:end]

            if component >= 0:
                yield JpegSegment(marker, marker_offset, payload, component)

            i = end
            if marker == SOS:
                in_scan = True

            if in_scan:
                # The outer loop searches for marker prefixes. Stuffed bytes
                # and restart markers are handled above; ordinary entropy bytes
                # are skipped one byte at a time.
                continue
