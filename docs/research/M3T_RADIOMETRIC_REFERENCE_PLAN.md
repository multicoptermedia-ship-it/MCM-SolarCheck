# M3T radiometric reference validation plan

Status: active research

## Confirmed local dataset facts

The 242 original M3T thermal files pass the structural extraction checks:

- 242/242 contain a 655,360-byte APP3 radiometric payload
- 640 x 512 x 16-bit = 327,680 raw samples per frame
- 242/242 contain one 256-byte APP4 block
- 242/242 contain one 23,818-byte APP5 block
- APP4 aligned float values at offsets 32, 36, 40, 44, 48 are constant across the dataset: 25.0, 5.0, 0.95, 0.5, 25.0
- global raw range observed: 17,112 .. 22,472
- frame mean range observed: 19,461.4687 .. 20,392.9123

These are raw radiometric values, not Celsius.

## Raster orientation check

A representative frame (`0200`) was compared against the embedded 640 x 512 rendered thermal JPEG. Pearson correlation between the decoded raw raster and rendered grayscale was approximately:

- native orientation: +0.764
- vertical flip: +0.518
- horizontal flip: -0.319
- both flips: -0.343

This strongly supports native row-major orientation for the raw raster. It is not yet a metrological proof because the rendered JPEG uses palette/range processing. The parser should therefore keep native orientation and mark orientation as structurally validated, pending reference-temperature comparison.

## DJI reference path

Current official DJI developer documentation confirms that the Mavic 3 Enterprise Series remains supported by DJI's developer platform. DJI documentation also distinguishes rendered 8-bit thermal imagery (temperature range mapped to 256 palette values) from temperature measurement APIs. Historical/current DJI SDK documentation exposes thermal scene/environment parameters such as emissivity, atmospheric temperature/transmission and background temperature.

For MCM-SolarCheck, live Mobile/Payload SDK temperature APIs are not a substitute for offline per-pixel conversion of archived R-JPEG/MPO files. The next reference requirement is an authoritative DJI offline radiometric conversion implementation/tool capable of producing a 640 x 512 temperature matrix from an original M3T thermal file.

## Acceptance test for Celsius conversion

No `temperature_celsius` matrix may be exposed by production code until a candidate converter passes all of the following against DJI reference output:

1. identical dimensions: 640 x 512;
2. verified raster orientation;
3. spot checks at corners, center and extrema locations;
4. frame minimum and maximum within an agreed tolerance;
5. representative module/ROI mean within an agreed tolerance;
6. parameter sensitivity behaves correctly when emissivity/distance/environment settings are varied;
7. repeated validation on multiple frames spanning the flight's raw-value range.

## Architecture rule

Keep the current raw parser vendor-neutral. Put DJI-specific Celsius conversion behind a provider interface. Never infer Celsius from the raw 16-bit values using an undocumented linear scale.

## Next implementation

Create a `ThermalTemperatureProvider` protocol and a DJI provider adapter stub. The adapter must fail explicitly with `TemperatureConversionUnavailable` until a validated DJI conversion backend is configured. This prevents accidental use of raw values as temperatures while allowing the rest of the MCM-SolarCheck pipeline to be developed and tested.
