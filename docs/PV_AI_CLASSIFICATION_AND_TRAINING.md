# PV AI taxonomy and opt-in training contract

Version 1 recognizes observable RGB and thermal *signatures* and records possible electrical causes separately. A hotspot is not proof of a bypass diode failure, PID, open circuit or insulation fault. Human review and electrical measurement may be required. EL/NIR with controlled electrical excitation is reserved for version 2; no EL imagery or calibration is available now.

Additional diagnostic hypotheses: open cell interconnects / detached front contacts / open substrings; insulation faults; string interruptions; cell fractures; shorted bypass diodes; open bypass diodes; potential-induced degradation (PID). These are hypotheses, not automatically confirmed YOLO detection classes.

Training candidates: align thermal anomaly with original high-resolution RGB frame via verified registration; mark an RGB-visible finding only if visually supported; expert confirms bounding box and label; check data quality, provenance and opt-in consent. Absence of a visible RGB anomaly is an explicit negative/unknown outcome, not a fabricated defect. Consent revocation must prevent future training use. Never auto-train or transfer customer images in this milestone.

Reports must describe observable evidence, reviewer conclusions, uncertainty and recommended electrical/EL follow-up; never invent temperatures or definitive diagnoses.
