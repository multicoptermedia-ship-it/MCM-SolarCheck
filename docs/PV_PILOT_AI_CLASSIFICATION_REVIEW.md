# AI classification in the pilot module report (block 35)

The shared offline/online pilot finding now supports an optional AI assessment. No inference model is connected in this block; no confidence or accuracy claim is made.

Three supported display states:
- **classified_suspicion:** "Verdacht auf <label>", never "electrical fault confirmed" from a thermogram alone.
- **unassigned:** anomaly recognized, cause cannot be assigned; recommend further inspection.
- **no_anomaly:** no anomaly detected by the model, not proof of absence of faults.

The human-reviewed observation remains mandatory for customer findings. AI classification and optional expert assessment appear as **separate** fields. When missing, both are marked not documented. Never fabricate model output or diagnostic evidence.

Existing findings without AI assessment remain compatible. No model was trained, downloaded, deployed, or licensed here. Future ingestion must record model version, data provenance, classification confidence and expert decision before customer release. A real confirmed electrical diagnosis needs independent supporting evidence.
