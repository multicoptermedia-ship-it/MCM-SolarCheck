"""Resolution-independent raw thermal analysis behind a declared extraction gate.

This adapter accepts ONLY an already-extracted, known-layout planar uint16
buffer. It does not parse DJI R-JPEG, proprietary thermal containers, XMP,
calibration coefficients, or claim radiometric Celsius temperatures.

The verified Mavic 3T APP3 decoder stays strict at its original 640x512 format.
A vendor-specific, validated decoder is required before actual 1024x768
camera files may be imported through this adapter.
"""
from __future__ import annotations

from dataclasses import dataclass
import struct

from .analysis import RawAnomalyCandidate, hottest_raw_candidates
from .m3t_radiometric import RadiometricRaster
from .quality import ThermalQualityResult, assess_raw_thermal_quality

MAX_DECLARED_THERMAL_PIXELS = 4_194_304


@dataclass(frozen=True)
class ExtractedRaw16Layout:
    width: int
    height: int
    byte_order: str
    extraction_provenance: str

    def __post_init__(self) -> None:
        if (
            type(self.width) is not int or type(self.height) is not int
            or self.width < 1 or self.height < 1
            or self.width * self.height > MAX_DECLARED_THERMAL_PIXELS
        ):
            raise ValueError("unsupported declared thermal pixel dimensions")
        if self.byte_order not in ("little", "big"):
            raise ValueError("explicit little or big endian raw16 samples required")
        if (
            not isinstance(self.extraction_provenance, str)
            or not self.extraction_provenance.strip()
        ):
            raise ValueError("documented extraction provenance required")


@dataclass(frozen=True)
class ExtractedThermalAnalysis:
    raster: RadiometricRaster
    quality: ThermalQualityResult
    candidates: tuple[RawAnomalyCandidate, ...]
    calibrated_temperature_c: None = None


def decode_extracted_raw16(
    samples: bytes, layout: ExtractedRaw16Layout,
    *, validated_extraction: bool,
) -> RadiometricRaster:
    """Decode a strictly framed raw buffer supplied by a verified extraction.

    No automatic dimension guesses, byte-order inference, or unverified
    fallback is allowed. The flag must originate from a trusted source
    adapter's validated format contract, never from image dimensions alone.
    """
    if not isinstance(layout, ExtractedRaw16Layout):
        raise TypeError("explicit extracted raw16 layout required")
    if validated_extraction is not True:
        raise ValueError("validated raw16 extraction is required")
    if not isinstance(samples, bytes):
        raise TypeError("raw16 samples must be immutable bytes")
    expected = layout.width * layout.height * 2
    if len(samples) != expected:
        raise ValueError("raw16 byte count does not match declared dimensions")
    endian = "<" if layout.byte_order == "little" else ">"
    unpacked = struct.unpack(f"{endian}{layout.width * layout.height}H", samples)
    return RadiometricRaster(
        width=layout.width, height=layout.height,
        byte_order=layout.byte_order, samples=unpacked, stream_offset=0,
    )


def analyse_extracted_raw16(
    samples: bytes, layout: ExtractedRaw16Layout,
    *, validated_extraction: bool,
    candidate_percentile: float = 99.9,
    candidate_limit: int = 100,
) -> ExtractedThermalAnalysis:
    """Run existing RAW-space quality and pixel-candidate logic at native size.

    Always returns uncalibrated raw sensor evidence, never degrees Celsius.
    """
    raster = decode_extracted_raw16(
        samples, layout, validated_extraction=validated_extraction,
    )
    quality = assess_raw_thermal_quality(
        raster, expected_width=layout.width, expected_height=layout.height,
    )
    if quality.grade.value == "reject":
        candidates = ()
    else:
        candidates = hottest_raw_candidates(
            raster, percentile=candidate_percentile, limit=candidate_limit,
        )
    return ExtractedThermalAnalysis(raster, quality, candidates)
