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

The production detector now invokes the ambiguity-aware gate, but the original gate remains the first decision path. The fallback is entered only after a cadence-not-confirmed result.

The fallback preserves every independently supported multiplier with at least two votes, enumerates phase/cell evidence, and accepts only when repeated finite lattice evidence identifies exactly one multiplier pair and exactly one phase. IoU ranking and matched-cell count cannot break a lattice tie.

Observed M3T validation cases motivating these invariants:

- 0055: 6x/10x has independently matched repeated-lattice evidence while the competing 4x/10x candidate does not; 9x/10x has no matched cell at the configured IoU threshold.
- 0056: competing cadence hypotheses produce no independently matched cell at the configured IoU threshold, so the fallback remains closed.
- 0061: both 3x/4x and 4x/4x have repeated-lattice-supported cells, so the fallback must remain ambiguous and reject.
- 0057, 0058, and 0060 do not establish robust two-axis candidate sets; 0059 does not establish two grid families.

These observations are validation fixtures, not permission to weaken any threshold. Missing, tied, or contradictory evidence remains a rejection.
