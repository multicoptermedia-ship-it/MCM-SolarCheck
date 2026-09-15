# M3T dataset validation – 2025-08-25 flight

Validation performed against all 242 original thermal files supplied for MCM-SolarCheck.

## Result

**PASS for structural radiometric extraction: 242 / 242 files.**

The sequence is complete from `0001` through `0242` with no missing sequence number.

Every file contains the same validated DJI radiometric marker structure when the marker stream is parsed sequentially by declared JPEG APP lengths rather than by searching marker byte patterns globally:

- APP3 segments: 11 per file
- first 10 APP3 payloads: 65,532 bytes each
- final APP3 payload: 40 bytes
- total APP3 radiometric payload: **655,360 bytes**
- expected raster: `640 * 512 * 2 = 655,360 bytes`
- APP4: exactly 1 block of 256 bytes per file
- APP5: exactly 1 block of 23,818 bytes per file

Thus all 242 files yield exactly **327,680 16-bit raw samples**, one sample per 640 x 512 thermal pixel.

## Raw-value sanity range

Decoded as little-endian unsigned 16-bit values (still NOT degrees Celsius):

- global minimum observed across the dataset: **17,112**
- global maximum observed across the dataset: **22,472**
- minimum frame mean: **19,461.47**
- maximum frame mean: **20,392.91**

These ranges are internally plausible and continuous for the flight, but Celsius conversion remains unvalidated.

## APP4 consistency

At 4-byte aligned offsets in the 256-byte APP4 block, the following little-endian float values occur identically in **all 242 files**:

- offset 32: `25.0`
- offset 36: `5.0`
- offset 40: `0.95`
- offset 44: `0.5`
- offset 48: `25.0`

The semantics of these fields are not yet treated as proven. `0.95` is consistent with a plausible emissivity setting, but field names must be validated against DJI reference behavior before production use.

## Important parser finding

A naive global byte search for `FF E3`, `FF E4`, `FF E5`, `FF D8`, or `FF D9` produces false positives because those byte sequences can occur inside raw radiometric data, JPEG entropy data, thumbnails, or auxiliary blocks.

During validation, naive global searches falsely suggested duplicate APP3/APP4/APP5 blocks in a small number of files. Sequential parsing from the first full DJI APP3 segment, advancing strictly by each segment's declared length, removes all of these false positives and produces an identical radiometric structure for 242/242 files.

This finding supersedes the earlier assumption that the radiometric APP3 blocks belong to a normal JPEG/MPO image component. In the validated M3T samples they form a dedicated contiguous DJI APP marker stream in the container layout.

## Parser requirement

Production parsing must:

1. locate a plausible DJI radiometric stream start (`APP3`, declared length 65534 / payload 65532);
2. advance sequentially by declared APP segment lengths;
3. concatenate only APP3 payloads in that validated chain;
4. require exactly 655,360 APP3 bytes;
5. require exactly one 256-byte APP4 block and one 23,818-byte APP5 block for this M3T format version;
6. decode the raw raster as little-endian uint16 provisionally;
7. expose raw values without a Celsius unit until temperature conversion is independently validated.

## Current conclusion

The supplied dataset is structurally suitable for continued MCM-SolarCheck development. No thermal frame needs to be rejected at the raw-radiometric extraction stage.

Next milestone: validate radiometric orientation and temperature conversion against an authoritative DJI reference implementation/output, then expose a calibrated 640 x 512 Celsius matrix through the thermal-provider adapter.
