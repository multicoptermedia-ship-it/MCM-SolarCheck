import struct

import pytest

from mcm_solarcheck.thermal.m3t_radiometric import M3TFormatError, M3TRadiometricParser


def segment(marker: int, payload: bytes = b"") -> bytes:
    return b"\xff" + bytes([marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def jpeg_component(app3_parts: list[bytes]) -> bytes:
    body = b"".join(segment(0xE3, part) for part in app3_parts)
    return b"\xff\xd8" + body + b"\xff\xd9"


def test_extracts_exact_640x512_uint16_payload():
    parser = M3TRadiometricParser()
    values = tuple(range(256)) * (parser.width * parser.height // 256)
    raw = struct.pack(f"<{len(values)}H", *values)
    data = jpeg_component([raw[:60_000], raw[60_000:]])

    raster = parser.parse_bytes(data)

    assert raster.width == 640
    assert raster.height == 512
    assert raster.pixel_count == 327_680
    assert raster.samples[:256] == tuple(range(256))
    assert raster.byte_order == "little"


def test_does_not_concatenate_app3_across_mpo_components():
    parser = M3TRadiometricParser()
    valid = b"\x01\x00" * (parser.width * parser.height)
    unrelated = b"not-radiometric"
    data = jpeg_component([unrelated]) + jpeg_component([valid])

    raster = parser.parse_bytes(data)

    assert raster.component_index == 1
    assert raster.samples[0] == 1
    assert raster.samples[-1] == 1


def test_rejects_wrong_payload_size():
    parser = M3TRadiometricParser()

    with pytest.raises(M3TFormatError, match="No component"):
        parser.parse_bytes(jpeg_component([b"too short"]))


def test_rejects_ambiguous_components():
    parser = M3TRadiometricParser()
    valid = b"\x00\x00" * (parser.width * parser.height)

    with pytest.raises(M3TFormatError, match="Ambiguous"):
        parser.parse_bytes(jpeg_component([valid]) + jpeg_component([valid]))
