# Block 37: customer report versus internal AI audit

Customer-facing PDF contains only reviewed observation, possible cause (as suspicion), and expert assessment. The rendering layer uses an allowlist rather than displaying the full internal provenance object.

Internal PilotAIProvenance remains available for model ID, version, input reference, confidence and reviewer decision. These are intentionally not rendered in the customer PDF. The confidence number is not a diagnostic probability.

No internal model or software architecture details should appear in customer exports by default. The normal customer report is not a technical model audit. Applicable contractual or legal transparency duties must still be evaluated separately.

Limitations: This change covers the pilot PDF presentation, not arbitrary logs, other export formats, file metadata, or access controls. Internal data must be protected through authorization and retention policies. This block does not run inference, release customer reports, or upload source imagery.
