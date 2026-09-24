# Phase 7 pretrained model intake

External models are **advisory evidence providers**. They never confirm a defect and
never replace expert review.

## Acceptance gate

A model may enter a production project only when all of the following are recorded:

1. modality (thermal or RGB) and expected preprocessing;
2. exact class taxonomy and its mapping into MCM candidate classes;
3. dataset/source identity and documented usage licence;
4. exact model/weights version and SHA-256 of the weight file;
5. inference backend/version and confidence threshold;
6. validation on representative MCM/DJI imagery before customer use.

Unknown classes map to `unknown`; `normal` is not a defect suggestion. A model
must not invent Celsius temperatures from rendered or 8-bit imagery.

## Current research shortlist (2026-09-24)

### PV-HSD-2025 — thermal hotspot candidate

The published dataset card describes 4,025 R-JPEG infrared defect images,
25,181 hotspot bounding boxes, YOLO annotations, Apache-2.0 licensing and
Ultralytics-compatible pretrained `.pt` resources. This is the closest current
match to our M3T thermal workflow.

Source: https://huggingface.co/datasets/MisakaMikoto128/PV-HSD-2025

**Status:** research/validation candidate only. The upstream README explicitly
states that the dataset and model resources are for academic research and that
commercial use requires author permission. This restriction takes precedence
over conflicting platform-level licence metadata for our intake decision.

A concrete small-model artifact is published as
`yolov8-p1-weights/pvhsd2025-yolov8s-p1.pt` (21,405,579 bytes), SHA-256
`f466bcc39afeed1389df40a487398bd6ca9137dbf649642f9a557ef63ec98bca`.
It may be used for controlled technical validation only until commercial model
and dataset rights are documented.

### pv-defect-detection-yolo — thermal hotspot/diode reference

This public MIT-licensed project documents a YOLO11n model fine-tuned for thermal
PV hotspot/diode detection, but the trained model is referenced through an
external Google Drive artifact. Repository licensing alone is not treated as
proof of the weight/dataset licence.

Source: https://github.com/reyhaneghaderi/pv-defect-detection-yolo

**Status:** architecture/reference candidate; do not import weights until artifact
licensing and provenance are independently verified.

### Curated PV thermal defects dataset — training/fine-tuning resource

Zenodo record 10.5281/zenodo.14644158 provides a 1.4 GB curated thermal defect
dataset assembled from five sources. It is useful for later validation or
fine-tuning, but it is a dataset rather than a drop-in production model.

Source: https://zenodo.org/records/14644158

## MCM integration rule

The first external model we trial should be thermal-first. RGB models remain a
separate evidence channel linked through `ImagePair`. Results are attached to a
physical `module_id`, retain source-frame/crop provenance, and remain
`classification_status=suggested` until a human review is recorded.
