# Cadence candidate evidence diagnostics

This diagnostic layer enumerates competing cadence multiples and phases without changing the production acceptance gate.

For every cell that already has independent image overlap above the configured IoU threshold, it records:

- cadence multipliers and phase indices;
- best independent-image IoU;
- number of finitely supported outer sides (0-4);
- finite internal lattice-line counts for both grid axes;
- the existing repeated-lattice predicate.

The report is intentionally observational. It must not create modules, choose a cadence merely because lattice evidence is present, or bypass the unique-cadence/phase requirements of the production detector.

The real-data workflow is: enumerate plausible multiplier pairs, compare supported phases, inspect outer and inner finite evidence, and only then decide whether a separately tested conservative acceptance rule is justified.


## Conservative ambiguity resolution

The production detector now invokes the ambiguity-aware gate, but the original gate remains the first decision path. The fallback is entered only after a cadence-not-confirmed result with at least one axis explicitly classified as `ambiguous_cadence`; missing or merely insufficient support cannot enter the fallback.

The fallback preserves every independently supported multiplier with at least two votes, enumerates phase/cell evidence, and accepts only when repeated finite lattice evidence identifies exactly one multiplier pair and exactly one phase. IoU ranking and matched-cell count cannot break a lattice tie. The selected candidate must also be one of the enumerated records, retain independently voted multipliers, and carry a valid in-range phase. That phase is propagated into module-cell generation and is not reselected by an IoU-only phase pass.

Observed M3T validation cases motivating these invariants:

- 0055: 6x/10x has independently matched repeated-lattice evidence while the competing 4x/10x candidate does not; 9x/10x has no matched cell at the configured IoU threshold.
- 0056: competing cadence hypotheses produce no independently matched cell at the configured IoU threshold, so the fallback remains closed.
- 0061: both 3x/4x and 4x/4x have repeated-lattice-supported cells, so the fallback must remain ambiguous and reject.
- 0057, 0058, and 0060 do not establish robust two-axis candidate sets; 0059 does not establish two grid families.

These observations are validation fixtures, not permission to weaken any threshold. Missing, tied, or contradictory evidence remains a rejection.


Candidate evidence is treated as an internal trust boundary. Malformed multiplier options, non-finite or out-of-range IoU values, inconsistent matched-cell counts, mismatched cell provenance, impossible outer-support counts, and malformed internal-lattice counts fail closed rather than participating in disambiguation.


## Phase 5 closure checks

The cadence safety path is regression-tested through repository head `18d5e5ceffc85184d3e815d9a862132c169a6c45` (CI run #257). The complete test matrix passed on that head.

The validated trust-boundary behavior now includes strict positive-integer image dimensions, finite quadrilateral candidate polygons, semantically consistent repeated-lattice flags and raw support counts, valid cadence multipliers/phases, finite positive cadence gaps, and in-range resolved phase indices. Malformed evidence fails closed.

Production module generation still has a stricter final requirement than the diagnostic repeated-lattice predicate: after cadence/phase resolution, generated cells pass `filter_cells_by_finite_support`, which requires finite support on all four outer sides. If that filter removes every cell, the detector returns no modules before image fusion. Independent image detections therefore cannot recreate grid cells rejected by finite-support validation.

### Real-image controls and scope

The development observations for M3T frames 0055, 0056 and 0061 above remain diagnostic evidence for the ambiguity rules. They are not labeled accuracy measurements and must not be presented as a post-change end-to-end benchmark. A fresh post-change image run is required before recording new detector counts. FDach remains outside development scope and reserved as holdout.

For Phase 5 closure, no threshold is relaxed to force a positive result. 0056 and tied 0061 evidence are expected to remain closed; 0055 may proceed only if the complete current production chain, including four-side finite support, independently validates the resulting cells.
