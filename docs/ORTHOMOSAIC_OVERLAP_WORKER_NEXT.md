# Next milestone: real pixel-level overlap worker

This block provides feature-match evidence structures, graph connectivity, conservative verdict rules and synthetic tests. It **does not yet extract or match features from original photos**. No successful orthomosaic or overlap measurement of the 29 DJI M3T pairs is claimed.

Worker acceptance criteria:
- Decode selected RGB frames locally; control image size, memory, CPU and concurrency.
- Extract scale-invariant local features, compare plausible neighbors plus loop closures, reject spurious repeated PV-cell matches using geometric verification and camera context.
- Record image IDs, inlier counts, robust geometric residuals and coverage; detect disconnected groups and weak image regions.
- Verify the whole flight and roof-plane group before publishing sufficient/insufficient status.
- Independently register RGB and thermal output in a shared module-plane grid and measure residual alignment.
- On genuinely insufficient overlap, emit exactly: „Keine Berechnung möglich, da die Bildüberlappung fehlerhaft ist.“
- Never treat feature connectivity alone as proof of complete coverage or reliable photogrammetry.

No cloud work, paid service, user image upload or production deployment is authorized.
