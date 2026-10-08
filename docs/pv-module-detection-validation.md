# PV module detection validation contract

The production path is conservative and fail-closed.

1. RGB module geometry is proposed from repeated structural grid lines.
2. Independent image evidence may confirm a grid cell but cannot create a module.
3. Geometry and image evidence that disagree produce no confirmed module.
4. All confirmed polygons pass the common image-boundary, area and duplicate gate.
5. Thermal findings may use these RGB modules only through a validated cross-sensor PixelTransform.

Development acceptance requires green unit/regression CI plus successful execution on the M3T RGB development set. Counts alone are not accuracy evidence; precision/recall requires labeled ground truth.

The FDach dataset is reserved as an untouched final holdout and must not be used for threshold selection or development.
