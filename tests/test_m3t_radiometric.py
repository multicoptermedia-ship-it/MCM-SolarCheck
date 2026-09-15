import struct
import pytest
from mcm_solarcheck.thermal.m3t_radiometric import APP4, APP5, M3TFormatError, M3TRadiometricParser


def segment(marker: int, payload: bytes = b"") -> bytes:
    return b"\xff" + bytes([marker]) + (len(payload) + 2).to_bytes(2, "big") + payload


def radiometric_stream(raw: bytes) -> bytes:
    parts = [raw[i:i + 65532] for i in range(0, len(raw), 65532)]
    return b"".join(segment(0xE3, p) for p in parts) + segment(APP4, bytes(256)) + segment(APP5, bytes(23818))


def test_extracts_exact_640x512_uint16_payload():
    parser = M3TRadiometricParser()
    values = tuple(range(256)) * (parser.width * parser.height // 256)
    raw = struct.pack(f"<{len(values)}H", *values)
    data = b"JPEG-prefix" + radiometric_stream(raw) + b"JPEG-suffix"
    raster = parser.parse_bytes(data)
    assert raster.pixel_count == 327_680
    assert raster.samples[:256] == tuple(range(256))
    assert raster.byte_order == "little"


def test_ignores_false_app3_signature_after_valid_stream():
    parser = M3TRadiometricParser()
    raw = b"\x01\x00" * (parser.width * parser.height)
    data = b"prefix" + radiometric_stream(raw) + b"\xff\xe3\xff\xfe" + b"noise"
    raster = parser.parse_bytes(data)
    assert raster.samples[0] == 1
    assert raster.samples[-1] == 1


def test_auxiliary_blocks_are_structurally_validated():
    parser = M3TRadiometricParser()
    raw = bytes(parser.expected_payload_size)
    blocks = parser.auxiliary_blocks(radiometric_stream(raw))
    assert len(blocks[APP4]) == 1 and len(blocks[APP4][0]) == 256
    assert len(blocks[APP5]) == 1 and len(blocks[APP5][0]) == 23818


def test_rejects_wrong_payload_size():
    parser = M3TRadiometricParser()
    bad = segment(0xE3, bytes(65532)) + segment(APP4, bytes(256)) + segment(APP5, bytes(23818))
    with pytest.raises(M3TFormatError, match="No validated"):
        parser.parse_bytes(bad)
