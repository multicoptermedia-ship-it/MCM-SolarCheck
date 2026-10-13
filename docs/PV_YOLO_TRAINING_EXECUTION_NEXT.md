# Training execution: remaining prerequisites

Milestone 18 creates deterministic content fingerprints and a metadata-only training plan after prior dataset audit and license checks. No model weights, datasets, network downloads, GPU usage or training runs were created.

Before actual training: link audit and fingerprint to the same immutable dataset snapshot (prevent time-of-check/time-of-use substitution); verify original publisher rights and any Ultralytics/model-weight license for commercial deployment; record group manifest checksum and approval; ensure customer opt-in and revocation controls for any customer-derived data; define reproducible runtime and dependencies; isolate training workers; enforce CPU/GPU time and cost budgets; evaluate once on held-out independent PV installations; publish per-class precision/recall and false positives with uncertainty. Thermal/RGB fusion requires verified geometric registration and expert review. EL is reserved for version 2.

The training plan is intentionally **not executable** and must never be interpreted as production approval.
