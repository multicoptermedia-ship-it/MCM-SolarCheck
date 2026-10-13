# Reproducible PV YOLO training preparation

A training plan is **not** permission to download weights, use unlicensed imagery, train on customer data or launch GPU jobs. Record immutable local dataset content hashes, a human-reviewed commercial license decision, explicit site/flight-disjoint train/val/test groups, RGB vs thermal modality, a reviewed observable-class vocabulary, model architecture/weights provenance, training seed and hyperparameters. Keep an independent test set untouched until final evaluation.

Thermal false-color JPEG does not establish radiometric Celsius. Electrical diagnoses (PID, diode faults, insulation failures) must not be treated as direct image ground truth. EL/NIR remains v2. This milestone prepares local, deterministic metadata only; no training runner or actual datasets.
