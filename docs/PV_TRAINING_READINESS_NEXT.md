# PV training readiness: milestone 17

Added: decoded JPEG/PNG image checks with compressed-byte, pixel and dimension caps; local read-only split audit; strict image/label one-to-one matching; valid empty negative annotations; mandatory site/flight IDs; group-disjoint train/val/test; modality, class mapping and commercial-license gates; synthetic regression tests.

Not yet a production import or training system: no image dataset was downloaded; no model was trained; no trained weights, actual RGB/thermal orthomosaics, inference, independent benchmark, customer consent workflow or report integration. `training_ready` is a **preliminary structural and license gate**, not scientific validation or final legal approval. Image decoding itself must be sandboxed for untrusted public files in a production worker.

Next: bounded dataset manifest with checksums, group provenance verification, dataset license evidence and human approval, class balancing and image-quality sampling, reproducible offline training config and independent field evaluation. Never derive definitive PID, insulation, diode or string diagnoses from a single image. EL remains v2.
