# Real M3T validation: segment-supported structural registration

## Scope

The current branch was evaluated against seven real DJI M3T RGB/thermal pairs from the supplied flight data: 0001, 0010, 0020, 0030, 0040, 0050 and 0062. Original customer/flight imagery is not committed to Git.

The evaluated pipeline is the current production candidate after introducing:

- finite-segment support for oriented structural intersections,
- bounded segment extension (`segment_extension_fraction=0.18`),
- native-pixel PV topology projection,
- topology-aware mutual-best cross-sensor matching.

No matching or validation threshold was relaxed to manufacture a successful registration.

## Current real-data result

| Pair | Thermal lines | Thermal supported junctions | RGB lines | RGB supported junctions | Accepted matches |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0001 | 120 | 21 | 120 | 300 | 0 |
| 0010 | 42 | 9 | 120 | 300 | 0 |
| 0020 | 66 | 11 | 120 | 300 | 0 |
| 0030 | 51 | 16 | 120 | 290 | 0 |
| 0040 | 48 | 16 | 120 | 300 | 0 |
| 0050 | 48 | 8 | 120 | 227 | 0 |
| 0062 | 30 | 3 | 120 | 300 | 0 |

The automatic registration therefore correctly remains fail-closed. None of the pairs provides the minimum ten reliable correspondences required by the current 6-point fit plus 4-point independent holdout policy.

## Diagnostic extension sweep

A diagnostic-only sweep was run to determine whether the bounded segment support itself is the sole bottleneck. These values were **not** adopted as production thresholds.

At extension 0.18 the thermal supported-junction counts are 21/9/11/16/16/8/3 and all pairs produce zero accepted matches. Increasing extension to 0.50 raises thermal junction counts to 37/15/24/26/26/20/7, but produces only one accepted match on pair 0001 and one on 0050. At the very permissive 0.80 extension, accepted matches are only 2/1/3/0/0/1/0.

This shows that simply extending detected segments cannot recover enough reliable cross-sensor correspondences. Relaxing segment support would reintroduce synthetic infinite-line intersections without solving the registration problem.

## Conclusion

The finite-segment filter is behaving as intended: it removes a large number of unsupported crossings, especially in thermal imagery. The remaining failure is structural and should not be addressed by lowering confidence thresholds.

The next registration block should move from independent junction descriptors to **global PV grid line-family reasoning**:

1. cluster long structural lines into the two dominant PV-grid orientation families per sensor;
2. order near-parallel lines by signed offset;
3. compare relative line-spacing sequences across thermal and RGB;
4. hypothesize family/index mappings;
5. derive control points from intersections of matched line indices;
6. retain RANSAC plus independent holdout as the final validation gate.

This uses the repeated module-grid structure directly and avoids asking locally ambiguous junctions to identify themselves independently.
