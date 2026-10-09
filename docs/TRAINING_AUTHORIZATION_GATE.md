# Current training permission gate

TrainingConsentService.require_granted verifies project ownership and the latest durable consent event. No permission or a withdrawal raises PermissionError. Online uploads with an unchecked consent box record withdrawal when the consent service is configured, preventing a prior project-level grant from silently remaining active.

This gate is not yet called by any training ingestion pipeline, because none is enabled. Upload storage and consent recording remain non-atomic. No deletion of training copies is implemented. Do not use customer images for training until consent, privacy, data-copy revocation, and retention workflows are end-to-end verified.
