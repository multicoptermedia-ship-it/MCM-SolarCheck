# Phase 7 dataset build gate

Before any MCM-owned model training run, the dataset build must be derived from an immutable training snapshot.

The build is accepted only when:

- every exported sample is human-reviewed and rights-approved through the snapshot gate;
- every source image is still present;
- every source image SHA-256 matches the digest recorded at corpus intake;
- correlated observations use inspection-level grouping when available, otherwise the physical module/finding grouping;
- train, validation and test assignment is deterministic;
- the build records the snapshot identifier, split policy, class distribution and split distribution;
- the resulting dataset manifest receives its own SHA-256 dataset identifier.

Changing image bytes after intake invalidates the build rather than silently training on different data. A missing source image also fails the build. Model training and deployment remain separate controlled steps; a successful dataset build does not authorize automatic retraining or customer deployment.
