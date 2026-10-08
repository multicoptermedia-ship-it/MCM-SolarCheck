# DJI Mavic 3 Thermal (M3T) – radiometric format notes

Status: research / provisional

This document records intermediate findings from analysis of an original MCM Mavic 3 Thermal dataset. The findings are intentionally kept separate from production code until the binary format and temperature conversion are validated.

## Dataset

- 242 thermal JPEG/MPO files
- Sequence: `0001` through `0242`
- Example naming: `DJI_20250825121339_0001_T.JPG`
- Thermal sensor raster: 640 x 512 pixels
- Expected thermal pixel count: 327,680
- Camera family: DJI Mavic 3 Thermal (M3T)
- DJI XMP metadata contains GPS/RTK, camera/gimbal and aircraft pose information.

## Radiometric payload observation

For normal samples, DJI-specific JPEG APP3 payloads associated with the thermal image produce a payload of exactly:

```
640 * 512 * 2 = 655,360 bytes
```

Interpreted as 16-bit samples this gives exactly 327,680 values, i.e. one value per 640 x 512 thermal pixel.

An investigated sample produced raw 16-bit statistics approximately:

- minimum: 18,160
- maximum: 20,352
- mean: 19,721.84
- median: 19,776

These values MUST NOT currently be interpreted directly as degrees Celsius. They are treated as radiometric/raw sensor values until DJI's conversion path or an independently validated conversion has been established.

## Additional DJI blocks

Additional DJI-specific data blocks have been observed, including a 256-byte parameter block and a larger auxiliary block. Float-like values observed in the parameter area include values such as `25.0`, `5.0`, `0.95`, `0.5`, and `25.0`.

`0.95` is a plausible emissivity value, but field meanings are NOT yet considered proven. No production parser should assign semantic names solely from these observations.

## MPO / JPEG parsing warning

The files may contain more than one JPEG image / MPO component. File `0001` demonstrated that concatenating every APP3 segment found anywhere in the complete file can yield a payload size different from 655,360 bytes.

Therefore the importer MUST:

1. parse JPEG/MPO image boundaries;
2. associate APP segments with the correct image component;
3. identify the thermal/radiometric component explicitly;
4. validate payload dimensions before decoding.

A naive global `APP3` concatenation is not acceptable.

## Architectural decision

MCM-SolarCheck should keep proprietary radiometric conversion behind a provider/adapter boundary.

```text
M3T R-JPEG / MPO
    |
    +-- MCM parser
    |     +-- EXIF/XMP
    |     +-- GPS/RTK
    |     +-- pose
    |     +-- JPEG/MPO structure
    |     +-- raw radiometric payload
    |
    +-- Thermal provider / DJI adapter
          +-- calibration parameters
          +-- validated raw -> temperature conversion
          +-- 640 x 512 Celsius matrix
```

This lets the core importer, geospatial model and anomaly pipeline remain vendor-neutral.

## Validation requirements before Celsius output

MCM-SolarCheck must not expose calculated Celsius temperatures until the conversion is validated against an authoritative DJI implementation and/or known reference measurements.

Validation should include:

- emissivity handling;
- reflected/apparent temperature parameters where applicable;
- target distance;
- humidity/atmospheric parameters where applicable;
- thermal calibration coefficients;
- raw matrix byte order and raster orientation;
- comparison of min/max/spot temperatures with a trusted DJI reference output.

## Next implementation milestone

Implement an `M3TRadiometricParser` that:

1. walks JPEG/MPO components safely;
2. records APP segment type, offset and size;
3. extracts only the radiometric APP3 payload belonging to the thermal component;
4. validates `655360` bytes for a 640 x 512 x 16-bit raster;
5. exposes the raw raster without claiming a temperature unit;
6. extracts auxiliary parameter blocks without assigning unverified semantics;
7. runs structural validation across all 242 samples.

Only after this stage should the DJI temperature-conversion adapter be connected.

## Data handling

Original customer/flight imagery should not be committed to the normal Git repository. Keep test fixtures small and anonymized. If binary reference data is later required, define an explicit test-data policy (for example Git LFS or an external/private fixture store) before adding it.
