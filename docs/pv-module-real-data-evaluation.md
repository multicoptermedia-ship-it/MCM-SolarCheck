# PV module detection — M3T development-data evaluation

Dataset: MCM-RGB1 (development data only; FDach remains untouched holdout).

Representative frames were evaluated with the production structural-grid and OpenCV image-evidence algorithms after the signed-normal intersection fix. Counts are diagnostics, not accuracy measurements.

| frame | structural lines | grid family sizes | grid cells | image candidates | confirmed IoU>=0.20 |
|---|---:|---|---:|---:|---:|
| 0001 | 120 | 16 / 13 | 180 | 7 | 6 |
| 0010 | 120 | 17 / 12 | 175 | 9 | 0 |
| 0020 | 120 | 19 / 16 | 206 | 11 | 1 |
| 0030 | 120 | 22 / 5 | 83 | 3 | 0 |
| 0040 | 120 | 19 / 8 | 102 | 2 | 0 |
| 0050 | 120 | 21 / 5 | 68 | 0 | 0 |
| 0055 | 120 | 18 / 11 | 146 | 10 | 2 |
| 0062 | 120 | 23 / 14 | 286 | 5 | 5 |

## Finding

The corrected intersection geometry executes consistently, but adjacent infinite grid-family lines generate far too many candidate cells. Independent image evidence rejects most of them, which is the intended fail-closed behavior, but the grid proposal stage is not yet physically constrained enough. The next improvement must require finite observed segment support around proposed cell boundaries rather than relaxing thresholds or accepting candidates from counts alone.

No precision/recall claim is made because these frames are not labeled ground truth.


## Phase 5 validation protocol after finite-support integration

The previous table is a pre-finite-support baseline and MUST NOT be reused as a post-change result. The next real-data run uses the same eight representative MCM-RGB1 frames, then all 62 MCM-RGB1 RGB frames, with the exact repository head. The run records grid/image/confirmed counts, statuses, exceptions and deterministic frame identity. Acceptance means execution and evidence-chain consistency only; it does not imply precision, recall, or field accuracy without independent labels.

FDach is explicitly excluded from development and remains reserved for final acceptance testing.
