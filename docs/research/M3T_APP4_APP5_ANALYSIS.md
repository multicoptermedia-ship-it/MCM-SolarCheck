# M3T APP4 / APP5 dataset analysis

Status: research / provisional

Dataset: 242 original DJI Mavic 3 Thermal images, sequence 0001-0242.

## Confirmed structural results

For every file, sequential JPEG marker parsing gives:

- APP3 radiometric payload: 655,360 bytes = 640 x 512 x 2
- APP4 payload: 256 bytes
- APP5 payload: 23,818 bytes

The APP5 block is byte-identical across all 242 files (one SHA-256 value). This strongly suggests a camera/calibration table or other static payload for this flight/camera rather than per-frame scene metadata. Its semantics remain unverified.

APP4 is not static: 194 distinct SHA-256 payloads occur across 242 frames. However, most of APP4 is constant.

## APP4 stable float candidates

Reading little-endian IEEE-754 floats at aligned offsets gives the following values in every one of the 242 frames:

| Offset | Value |
|---:|---:|
| 32 | 25.0 |
| 36 | 5.0 |
| 40 | 0.949999988... |
| 44 | 0.5 |
| 48 | 25.0 |

These values are highly plausible radiometric/environment parameters, especially 0.95 as an emissivity-like value. Their exact DJI field names MUST NOT be asserted until validated against an authoritative DJI reference or known SDK output.

## APP4 changing bytes

Only 25 byte positions vary across the dataset:

- offsets 9 through 31
- offsets 96 and 97

The changing region at 9-31 contains structured non-random values and sometimes 0xFF fill values. Offsets 96-97 also change over the flight. These fields require further decoding before assigning semantics.

## Important correction to earlier assumptions

APP4 is therefore not fully constant across the flight. The five obvious float candidates at offsets 32-48 are constant, while other APP4 fields are frame-dependent.

APP5, in contrast, is fully byte-identical across the 242-file dataset.

## DJI reference implications

DJI's official SDK documentation confirms that thermal measurement involves parameters such as scene emissivity, background/reflected temperature, atmospheric temperature/transmission and temperature measurement output in degrees Celsius. This supports keeping environmental/calibration data separate from the raw APP3 raster, but it does not by itself prove the private APP4 binary field mapping.

## Next validation step

1. Decode APP4 offsets 9-31 and 96-97 by correlation with frame time, raw statistics and other metadata.
2. Characterize APP5 internal structure and look for calibration tables/coefficient patterns without assigning unsupported semantics.
3. Obtain authoritative DJI offline/R-JPEG temperature output for selected frames.
4. Compare DJI Celsius values against APP3 raw pixels and APP4/APP5 parameters.
5. Only then implement production Celsius conversion.
