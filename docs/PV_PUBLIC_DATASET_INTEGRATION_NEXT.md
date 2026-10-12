# Public dataset integration: next gates

Implemented: candidate source register; strict license/modality approval record; parser for normalized YOLO detection annotations; train/validation/test site/flight isolation validator; regression tests.

Not implemented: dataset downloads, VOC-to-YOLO conversion, image integrity checks, full dataset ingestion, model training, inference, RGB/thermal alignment, expert-review UI, or report linkage. These remain separate milestones.

Next: verify original rights and exact image modalities, obtain source checksums and documented commercial permissions, review class mappings against observable signatures (never map an image pattern directly to PID/diode diagnosis), add a bounded local-only dataset importer, then evaluate pretrained models on a held-out site-separated benchmark. Customer samples require active opt-in consent and expert labels. Do not add datasets or weights to Git.
