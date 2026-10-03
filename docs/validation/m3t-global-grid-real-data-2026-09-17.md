# Real M3T global-grid registration baseline

Date: 2026-09-17

## Scope

Independent diagnostic run of the production global-grid components at commit `0369bb4819a294da2aebbfd971076b052915044a` against the existing flat-roof development dataset only. Original imagery is not committed. The reserved pitched-roof dataset (`FDach.zip`) was not inspected or used for parameter selection.

Pairs: `0001`, `0010`, `0020`, `0030`, `0040`, `0050`, `0062`.

Production defaults were preserved: structural detector blur 5x5, max dimension 900, minimum family lines 4, maximum spacing error 0.22, ambiguity margin 0.03, minimum fit points 6, minimum independent holdout points 4. No acceptance threshold was loosened.

## Results

| Pair | T lines | RGB lines | T families (angle/lines) | RGB families (angle/lines) | accepted family matches | control points | result |
|---|---:|---:|---|---|---:|---:|---|
| 0001 | 120 | 120 | 1.8°/8, 92.1°/6 | 2.6°/65, 92.1°/5 | 1 | 0 | refused |
| 0010 | 42 | 120 | 3.5°/5, 93.5°/5 | 135.7°/8, 43.9°/17 | 1 | 0 | refused |
| 0020 | 66 | 120 | 162.2°/10, 71.0°/7 | 164.6°/30, 72.6°/20 | 1 | 0 | refused |
| 0030 | 51 | 120 | 3.6°/6 | 38.2°/5 | 0 | 0 | refused |
| 0040 | 48 | 120 | 3.6°/7, 94.6°/4 | 3.7°/51, 92.2°/18 | 1 | 0 | refused |
| 0050 | 48 | 120 | 5.3°/6, 95.1°/4 | 172.5°/14, 95.7°/4 | 0 | 0 | refused |
| 0062 | 30 | 120 | 92.8°/7, 3.0°/4 | 1.8°/62, 92.5°/27 | 1 | 0 | refused |

No pair reached the two-family requirement, therefore no production control-point set or homography was accepted. This is the correct fail-closed behavior.

## Diagnostic interpretation

The current bottleneck is before homography fitting. In several pairs both sensors contain two plausible near-orthogonal families, but repetitive module spacing makes one family ambiguous and the conservative family matcher rejects it. Pair 0010 also exposes a detector failure mode: the RGB family seed is dominated by diagonal cell texture rather than the physical module grid. This confirms the previously identified risk of selecting a family from the longest structural line alone.

A strictly exploratory stronger RGB blur (9x9) was also tried without changing acceptance thresholds. It suppressed cell texture enough for pair 0010 to produce two family matches and 16 control points, but the independent holdout still rejected the resulting homography (RMS 26.29 px, max 29.91 px). This is useful negative evidence: preprocessing alone must not be treated as validation, and thresholds must not be relaxed to force acceptance.

## Next engineering step

Improve PV-grid family extraction/matching using structural support rather than a single longest-line seed, while retaining the independent holdout gate. Add synthetic regression tests for cell-texture/spurious-line dominance before changing production behavior. Re-run this exact seven-pair baseline after the tested change.
