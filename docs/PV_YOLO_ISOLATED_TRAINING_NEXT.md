# Next implementation: isolated offline YOLO training

1. Stage a read-only, content-addressed dataset copy in a sandbox with strict storage and file limits, then verify against the approved snapshot.
2. Require explicit operator consent for a local training run; never download external weights automatically. Confirm both dataset and Ultralytics/model licensing for intended commercial use.
3. Pin runtime/library versions and deterministic seeds, bound CPU/GPU memory and runtime, and capture structured logs without image pixels or sensitive paths.
4. Keep the test split sealed until final evaluation; report class-wise precision/recall, false positives, site-wise breakdown, calibration and domain shift.
5. Register a trained model only after independent field validation and expert review. Thermal hot spots are observations, not proof of PID, insulation, diode or string failures.

Current snapshot/gate is metadata-only; no model trained, no images transferred, no orthomosaic inference. EL remains version 2.
