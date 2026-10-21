"""Declared high-resolution raw16 evidence without claiming vendor-file support.

These tests supply extracted sample bytes explicitly. They do not use actual
DJI files, measure real temperatures or approve an unknown camera decoder.
"""
from array import array
import struct
import sys

import pytest

from mcm_solarcheck.thermal.declared_raw16 import (
    MAX_DECLARED_THERMAL_PIXELS, ExtractedRaw16Layout,
    analyse_extracted_raw16, decode_extracted_raw16,
)
from mcm_solarcheck.thermal.m3t_radiometric import M3TFormatError, M3TRadiometricParser
from mcm_solarcheck.thermal.quality import ThermalQualityGrade, assess_raw_thermal_quality


WIDTH, HEIGHT = 1024, 768


def raw_1024_by_768():
    # A varied but fully synthetic sensor-value plane with a hotspot at the
    # final native pixel. No absolute temperature inference.
    values = array("H", (19000 + i % 1000 for i in range(WIDTH * HEIGHT)))
    values[-1] = 65000
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def layout(width=WIDTH, height=HEIGHT, byte_order="little"):
    return ExtractedRaw16Layout(
        width=width, height=height, byte_order=byte_order,
        extraction_provenance="synthetic declared raw16 test provider",
    )


def test_1024x768_native_thermal_analysis_identifies_exact_hotspot_pixel():
    extracted = analyse_extracted_raw16(
        raw_1024_by_768(), layout(),
        validated_extraction=True,
        candidate_limit=4,
    )
    assert (extracted.raster.width, extracted.raster.height) == (WIDTH, HEIGHT)
    assert extracted.raster.pixel_count == 786432
    assert extracted.raster.samples[-1] == 65000
    assert extracted.quality.grade == ThermalQualityGrade.PASS
    assert extracted.calibrated_temperature_c is None
    assert (extracted.candidates[0].x, extracted.candidates[0].y) == (1023, 767)
    assert extracted.candidates[0].raw_value == 65000
    assert 0 < len(extracted.candidates) <= 4
    assert all(0 <= c.x < WIDTH and 0 <= c.y < HEIGHT for c in extracted.candidates)


def test_m3t_default_quality_and_parser_do_not_silently_accept_new_camera():
    payload = raw_1024_by_768()
    raster = decode_extracted_raw16(payload, layout(), validated_extraction=True)
    # Vendor-specific 640x512 quality and format constraints remain unchanged.
    ordinary_m3t_gate = assess_raw_thermal_quality(raster)
    assert ordinary_m3t_gate.grade == ThermalQualityGrade.REJECT
    assert "expected 640x512" in ordinary_m3t_gate.reasons[0]
    with pytest.raises(M3TFormatError, match="No validated"):
        M3TRadiometricParser().parse_bytes(payload)


def test_declared_raw16_handles_big_endian_and_exact_dimensions():
    raw = struct.pack(">6H", 1, 2, 65530, 100, 500, 900)
    spec = layout(width=3, height=2, byte_order="big")
    raster = decode_extracted_raw16(raw, spec, validated_extraction=True)
    assert raster.samples == (1, 2, 65530, 100, 500, 900)
    assert raster.byte_order == "big"
    assert raster.pixel_count == 6
    assert raster.stream_offset == 0


@pytest.mark.parametrize("width,height", [
    (0, 768), (1024, 0), (-1, 768), (True, 768), (1024, False),
    (MAX_DECLARED_THERMAL_PIXELS + 1, 1),
])
def test_invalid_or_unbounded_declared_dimensions_rejected(width, height):
    with pytest.raises(ValueError, match="dimensions"):
        layout(width=width, height=height)


@pytest.mark.parametrize("order", ["unknown", "", None, "LE", 0])
def test_byte_order_must_be_explicit_and_known(order):
    with pytest.raises(ValueError, match="little or big"):
        layout(byte_order=order)


@pytest.mark.parametrize("provenance", ["", " ", None, 123, False])
def test_extraction_origin_must_be_documented(provenance):
    with pytest.raises(ValueError, match="provenance"):
        ExtractedRaw16Layout(1024, 768, "little", provenance)


def test_unvalidated_extraction_is_blocked_before_candidate_analysis():
    spec = layout(2, 2)
    raw = struct.pack("<4H", 1, 2, 3, 4)
    for invalid in (False, None, 1, "yes"):
        with pytest.raises(ValueError, match="validated"):
            decode_extracted_raw16(raw, spec, validated_extraction=invalid)
        with pytest.raises(ValueError, match="validated"):
            analyse_extracted_raw16(raw, spec, validated_extraction=invalid)


def test_wrong_length_rejected_instead_of_inferred_or_padded():
    spec = layout(3, 2)
    raw = struct.pack("<6H", 10, 20, 30, 40, 50, 60)
    for invalid in (raw[:-1], raw + b"\x00", b""):
        with pytest.raises(ValueError, match="byte count"):
            decode_extracted_raw16(
                invalid, spec, validated_extraction=True,
            )
    with pytest.raises(TypeError, match="immutable bytes"):
        decode_extracted_raw16(
            bytearray(raw), spec, validated_extraction=True,
        )


def test_no_celsius_claim_and_no_artificial_sample_scaling():
    layout_small = layout(width=4, height=2)
    raw = struct.pack("<8H", 100, 200, 300, 400, 500, 600, 700, 30000)
    result = analyse_extracted_raw16(
        raw, layout_small, validated_extraction=True,
        candidate_percentile=90, candidate_limit=2,
    )
    assert result.raster.samples[-1] == 30000
    assert result.calibrated_temperature_c is None
    assert result.quality.statistics.maximum == 30000
    assert result.candidates[0].raw_value == 30000


def test_explicit_layout_type_gate():
    with pytest.raises(TypeError, match="layout"):
        decode_extracted_raw16(
            b"\x01\x00", {"width": 1}, validated_extraction=True,
        )
