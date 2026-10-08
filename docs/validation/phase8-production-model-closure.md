# Phase 8 production-model pipeline closure

Phase 8 is technically complete when the CI gate for this document is green. This closure records implemented contracts; it does **not** claim that a production detector has already been scientifically validated on a sufficient real-world M3T corpus or that third-party commercial rights have been cleared.

## Implemented acceptance gates

1. Reviewed detector/segmenter geometry is explicit persisted evidence. Geometry is bounded against its source representation and included in snapshots only for current trainable ground-truth labels.
2. Backend-neutral training rows preserve immutable label and source-frame identity. YOLO detection export supports multiple objects per image, safe filenames, class-map validation, byte-hash preflight and immutable output.
3. Dataset splitting preserves inspection-group isolation and deterministic train/validation/test assignment.
4. Training lineage records exact dataset/snapshot, backend/version, preprocessing, parameters and explicit seed. The controlled Ultralytics adapter rejects configuration drift and output weights receive SHA-256 identity.
5. Model evaluation has its own deterministic provenance. Release-bound evaluation must use a dataset and snapshot distinct from training and must satisfy the acceptance policy on representative M3T imagery.
6. RGB and thermal remain distinct modalities; module/ImagePair identity is the cross-modal boundary. No pixel-coordinate equivalence is assumed.
7. External models remain subject to documented rights and validation gates. Research-only or otherwise unverified weights are not customer-release inputs.
8. A validated release remains advisory evidence. Release provenance reaches the finding, but only human review can make the authoritative finding decision.
9. ModelPackageManifest binds release/run/weights/backend/preprocessing and blocks weight distribution until distribution rights are explicitly verified.
10. Phase-8 end-to-end and fail-closed tests cover reproducible training lineage, independent validation, release provenance, human authority, nonrepresentative validation and insufficient-recall rejection.

## Commercialization boundary

Customer distribution remains a separate release gate documented in `docs/validation/commercialization-license-gate.md`. Phase 8 does not approve an MCM application EULA, dependency licenses, external model/dataset rights, basemap terms or redistribution of third-party weights.

## Preserved safety semantics

- New M3T material may enter the corpus automatically, but starts unlabeled and rights-unverified.
- Predictions never become trusted training labels automatically.
- Raw radiometric values are never converted into synthetic Celsius values.
- Physical PV module identity is the service target; absolute hotspot GPS is not fabricated.
- Model output remains a suggestion until a human reviewer decides the finding.

## Remaining product work after Phase 8

The next phase may integrate the validated contracts into the desktop workflow, real representative model experiments and packaging. A scientifically validated production model still requires real held-out M3T evaluation data and the commercialization gate must be satisfied before customer distribution.
