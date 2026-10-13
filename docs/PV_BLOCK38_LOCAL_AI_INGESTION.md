# Block 38

Local detector results can be staged with a pending review decision. No inference engine is connected. Human review and customer-release enforcement remain required before production use.

## Block 38.2 – offline-first bridge (five-step round)

The shared-domain bridge `vertical_local_ai_candidate_bridge.stage_local_ai_candidates`
converts validated `LocalAIResult` suggestions to `Finding` candidates. It is
pure, local, and does not run inference, transmit data, approve a report, or
write to a customer-facing artifact.

Safety boundaries:
- An existing imported candidate analysis with paired RGB/thermal evidence is required.
- Each new AI suggestion must refer to a thermal frame already present in that
  analysis; its model input reference must match that frame ID.
- Candidate IDs must be unique, and pixel coordinates must be non-negative integers.
- AI model metadata and status are validated by the existing ingestion contract.
- New findings remain `unreviewed` with type `local_ai_suggestion_unverified`.
- The existing `LocalReviewDraft`, expert review, report approval, and separately
  authorized export gates must be used downstream.
- The bridge intentionally does **not** put internal model metadata into a
  customer report. Model provenance needs a separate, access-controlled
  internal audit store before production integration.
- This is not a detector integration or proof of real model accuracy. A
  production adapter must additionally verify frame ownership, module
  geometry, image bounds, and source-file provenance.

Quality gate: run all targeted tests and full Python 3.11/3.12 CI. This round
is not considered verified until those checks are green. Keep the common
core reusable by online adapters; finish the offline vertical workflow first.
