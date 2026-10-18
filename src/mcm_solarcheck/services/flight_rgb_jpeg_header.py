"""Conservative JPEG SOF dimension scan without decoding image pixels.

Supports ordinary baseline/progressive JPEG SOF markers. Fails closed on
truncated, malformed or unsupported JPEG headers.
"""
from pathlib import Path

_SOF = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def jpeg_dimensions(path, *, max_header_bytes=1_048_576):
    if type(max_header_bytes) is not int or max_header_bytes < 16:
        raise ValueError("invalid JPEG header budget")
    source = Path(path)
    if source.is_symlink() or not source.is_file():
        raise ValueError("regular JPEG required")
    with source.open("rb") as stream:
        if stream.read(2) != b"\xff\xd8":
            raise ValueError("invalid JPEG signature")
        scanned = 2
        while scanned < max_header_bytes:
            marker_start = stream.read(1)
            scanned += 1
            if marker_start != b"\xff":
                raise ValueError("malformed JPEG marker")
            marker = stream.read(1)
            scanned += 1
            while marker == b"\xff" and scanned < max_header_bytes:
                marker = stream.read(1)
                scanned += 1
            if not marker or marker in (b"\x00", b"\xd9", b"\xda"):
                raise ValueError("JPEG SOF missing")
            value = marker[0]
            if value in (0x01, *range(0xD0, 0xD9)):
                continue
            length_data = stream.read(2)
            scanned += 2
            if len(length_data) != 2:
                raise ValueError("truncated JPEG segment")
            length = int.from_bytes(length_data, "big")
            if length < 2 or scanned + length - 2 > max_header_bytes:
                raise ValueError("JPEG header budget exceeded or invalid")
            if value in _SOF:
                payload = stream.read(length - 2)
                if len(payload) < 6:
                    raise ValueError("truncated JPEG SOF")
                height = int.from_bytes(payload[1:3], "big")
                width = int.from_bytes(payload[3:5], "big")
                if width < 1 or height < 1:
                    raise ValueError("invalid JPEG dimensions")
                return width, height
            stream.seek(length - 2, 1)
            scanned += length - 2
    raise ValueError("JPEG SOF outside header budget")
