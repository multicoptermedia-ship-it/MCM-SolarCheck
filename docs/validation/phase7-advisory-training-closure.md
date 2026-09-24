# Phase 7 advisory model and training-data closure

Phase 7 closes the software boundary between imported M3T evidence, a growing
reviewed training corpus, controlled model lineage, advisory inference, and the
final human inspection decision.

## Closed invariants

- Every imported M3T image may be indexed into the training corpus automatically,
  but new material starts unlabeled and with unverified rights.
- Content SHA-256 provides immutable byte identity while project, source frame,
  modality, review state, and rights remain source-specific provenance.
- Identical bytes in different projects or source-frame occurrences do not move
  rights or review state between those sources.
- Only human-reviewed, rights-approved samples can enter a training snapshot.
- Ground-truth corrections are append-only and must supersede the current label
  head while preserving inspection-group identity.
- Dataset construction verifies source bytes against the snapshot and rejects
  missing/tampered files, empty reviewed datasets, and UNKNOWN ground truth.
- Training runs bind dataset ID, snapshot ID, trainer/version, preprocessing, and
  parameters before weight artifacts are accepted.
- Resulting weights are SHA-256 identified. A rejected validation cannot produce
  a model release.
- External/customer model use fails closed unless both required usage rights and
  representative M3T validation are documented.
- Raw radiometric matrices cannot silently enter an inference contract trained
  for rendered RGB/grayscale imagery.
- Model output is advisory evidence only. A suggestion does not alter
  `reviewer_status`; only explicit human review can confirm/reject/mark unclear.
- Advisory evidence is module-scoped. The physical PV module remains the service
  target; no synthetic hotspot GPS coordinate is required.
- Release, training run, weights, dataset, snapshot, model/dataset manifest,
  source frame, module crop, and classification provenance remain auditable.

## Schema and migration

Training-corpus schema v11 identifies a source occurrence by
`(project_id, source_frame_id, modality)`. The explicit v10 -> v11 migration
preserves existing corpus rows and review/rights state. Unsupported historical
versions remain fail-closed rather than being guessed into a migration.

## Acceptance tests

The Phase 7 end-to-end acceptance regression exercises:

`M3T source -> corpus -> human ground truth -> rights approval -> snapshot ->
dataset -> controlled training -> weight digest -> validation -> release ->
module-scoped advisory -> release provenance -> human decision`.

The fail-closed acceptance suite separately checks missing model rights, missing
M3T validation, raw-radiometric inference misuse, rejected model release, empty
training data, and the invariant that machine suggestion metadata cannot create
a human review decision.

CI run #429 passed the complete test matrix with the positive end-to-end
acceptance path. CI run #430 passed the complete matrix after adding the
fail-closed acceptance gates.

## Scope deliberately left for Phase 8

Phase 7 does not claim that a production defect detector has already been
trained or scientifically validated. Detection/segmentation geometry export,
larger representative M3T validation cohorts, trainer/backend integration,
model-quality benchmarking, and production deployment remain subsequent work.

Commercialization is also a separate release gate. External datasets, model
weights, dependencies, map providers, and bundled assets require documented
rights appropriate to the intended distribution before customer release.

## Closure

Phase 7 is closed at the architecture and software-contract level: MCM-SolarCheck
can grow a provenance-preserving training corpus without treating new images or
machine suggestions as truth, can bind trained artifacts to reproducible
lineage, can reject unsafe/unauthorized model paths, and retains human review as
the authoritative inspection decision.
