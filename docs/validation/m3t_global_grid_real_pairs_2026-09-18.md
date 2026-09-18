# Real M3T global-grid registration validation — 2026-09-18

Development dataset only. The independent FDach holdout dataset was not used.

Exact repository gate before this run: `e2d6d6f1f428a961aa6b7e34da1d00c41d2a231f`; GitHub Actions run #82 completed successfully.

Representative paired sequences: 0001, 0010, 0020, 0030, 0040, 0050, 0062.

| Seq | Thermal structural lines | RGB structural lines | Thermal grid families (angle°, lines) | RGB grid families (angle°, lines) | Production family matches |
|---|---:|---:|---|---|---:|
| 0001 | 120 | 120 | (1.95,7), (92.08,6) | (2.56,65), (92.08,5) | 0 |
| 0010 | 42 | 120 | (93.47,5), (3.51,5) | (82.83,27), (5.04,15) | 0 |
| 0020 | 66 | 120 | (162.18,10), (71.00,7) | (169.26,41), (77.10,34) | 0 |
| 0030 | 51 | 120 | (3.56,6) | (3.62,64) | 0 |
| 0040 | 48 | 120 | (3.59,7), (94.58,4) | (3.74,51), (91.34,16) | 0 |
| 0050 | 48 | 120 | (5.25,6), (95.13,4) | (4.44,62), (95.71,4) | 0 |
| 0062 | 30 | 120 | (92.78,7), (3.02,4) | (1.81,62), (92.49,27) | 0 |

All seven pairs correctly fail closed at the production family-matching gate. No registration was accepted and therefore no homography/holdout quality is reported.

A diagnostic-only run with the per-family ambiguity margin set to zero was used to identify the bottleneck, not to change production acceptance thresholds. It produced two family matches only for 0020, 0040 and 0062. 0040 had rotations +0.15°/-3.24° with spacing scores 0.1294/0.1181; 0062 had -0.29°/-1.21° with scores 0.1357/0.1564. Sequence 0020 exposed an important remaining ambiguity: a swapped-axis mapping can have internally consistent rotations (-85.08°/-81.74°), so common-rotation consistency alone does not prove the physically correct axis permutation.

Conclusion: the dominant current bottleneck is cross-resolution grid representation and repeated-spacing ambiguity, not homography validation. RGB extraction often produces many more distinct offsets than thermal (for example 65 vs 7 in sequence 0001). Do not relax registration validation thresholds. Next work should add a physically justified axis-orientation prior/metadata constraint and improve module-grid line selection before attempting homography acceptance.
