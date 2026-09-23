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
