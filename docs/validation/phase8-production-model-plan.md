# Phase 8 plan: production model pipeline

Phase 7 established the provenance, rights, validation, advisory-inference, and
human-review contracts. Phase 8 builds production training and evaluation on
those contracts without weakening them.

## Objectives

1. Export detector/segmenter geometry together with reviewed module/finding
   labels; never synthesize geometry that was not reviewed or derived from a
   validated source.
2. Build a backend-specific YOLO dataset adapter on top of the backend-neutral
   snapshot/dataset manifest.
3. Preserve inspection-group split isolation so related images/modules cannot
   leak between train, validation, and test sets.
4. Introduce an explicit trainer backend/version contract and record the exact
   preprocessing, parameters, seed, dataset ID, snapshot ID, and output digest.
5. Evaluate on representative M3T imagery that is separate from training data,
   with defect recall and false-positive behavior reported by canonical class.
6. Keep RGB and thermal as separate evidence modalities. Cross-modal fusion must
   resolve through physical module identity/ImagePair rather than pretending
   pixel coordinates are interchangeable.
7. Compare an MCM-trained baseline with legally usable external candidates only
   when their dataset/weight rights are documented for the intended use.
8. Require validation acceptance before a trained artifact can become a release;
   release still creates advisory evidence, never an automatic diagnosis.
9. Add reproducible model-package metadata for later desktop distribution,
   without bundling weights whose distribution rights are not verified.
10. Finish with an end-to-end production-model acceptance gate and update the
    commercialization/license checklist before customer release.

## First implementation slice

The first slice is the reviewed geometry contract. Training export currently
carries class and source provenance but intentionally has no detector bounding
box or segmentation polygon. Phase 8 will add geometry as explicit reviewed
training evidence, validate coordinates against the source representation, and
export only labels whose geometry contract is complete for the selected task.

This keeps classification-only ground truth valid for classification workflows
while preventing it from being silently promoted into detector ground truth.

## Non-goals

Phase 8 will not infer absolute hotspot GPS coordinates, turn raw thermal values
into Celsius without calibration provenance, auto-approve new corpus material,
or allow model predictions to feed themselves back as trusted labels.
