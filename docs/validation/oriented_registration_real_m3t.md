# Real M3T oriented structural registration validation

Dataset: MCM RGB/thermal flight, 2025-08-25. Original imagery is intentionally not committed.

Representative paired sequences tested: 0001, 0010, 0020, 0030, 0040, 0050, 0062.

The current oriented structural pipeline was reproduced against the original local M3T images using the same line detector, oriented intersection construction and conservative mutual-best matcher defaults (`max_score=0.2`, `ambiguity_margin=0.025`, crossing-angle delta <= 12 deg).

| sequence | thermal lines | thermal points | RGB lines | RGB points | accepted matches |
|---:|---:|---:|---:|---:|---:|
| 0001 | 120 | 300 | 120 | 300 | 0 |
| 0010 | 100 | 221 | 120 | 300 | 1 |
| 0020 | 120 | 300 | 120 | 300 | 5 |
| 0030 | 120 | 200 | 120 | 300 | 0 |
| 0040 | 120 | 297 | 120 | 300 | 0 |
| 0050 | 101 | 234 | 120 | 300 | 0 |
| 0062 | 95 | 300 | 120 | 300 | 0 |

For sequence 0020 the five accepted descriptor scores were approximately 0.039, 0.028, 0.066, 0.048 and 0.054. This is still below the minimum of ten correspondences required for six fit points plus four independent validation points.

## Conclusion

Orientation context improves discrimination but is not sufficient for automatic production registration on this representative real dataset. No threshold was relaxed and no homography was forced. The correct fail-closed outcome remains `insufficient_oriented_structural_matches`.

The next matcher stage should exploit PV-grid topology rather than treating junctions as independent local points. Candidate correspondences should be constrained by repeated row/column spacing, dominant grid axes and neighbourhood ordering before RANSAC. Registration may only become usable after independent holdout reprojection validation passes.
