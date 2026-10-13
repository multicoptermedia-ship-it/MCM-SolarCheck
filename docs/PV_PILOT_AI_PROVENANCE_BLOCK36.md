# Block 36: auditable AI-result metadata

The offline/online shared pilot contract can now carry an optional model ID, model version, local input reference, numerical model confidence (0..1), and a reviewer decision: pending, accepted, corrected, rejected.

Model confidence is explicitly **not** a probability of a correct electrical diagnosis. Missing model data remains "nicht erfasst". This block does **not** implement model execution, train weights, download datasets, or transmit customer images.

The expert-reviewed finding text is still required by PilotReport. Reviewer decision metadata documents handling of a model suggestion; it is not itself evidence that an electrical failure is confirmed. Real production ingestion must verify that the referenced local image and model/version correspond to the evaluated input and must implement a separate release gate for pending decisions.

No proprietary inference license or cloud cost is introduced.
