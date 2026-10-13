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

## Block 38.3 – report release and module evidence gate

The shared report adapter now refuses to publish a candidate retaining the
internal `local_ai_suggestion_unverified` label, even after expert acceptance.
A separate expert-confirmed, customer-safe finding label must be supplied
through the existing review/report workflow; a decision alone does not rename
a candidate. No automatic label transformation is introduced.

The offline-first candidate bridge now also requires the AI module identifier
to be present in imported module evidence. This is a conservative interim
check, **not** a geometric or frame-specific verification. A production
adapter still needs authoritative per-frame module mapping, image bounds,
model provenance storage, and an explicit expert correction mechanism.

New regression tests cover the report gate and unknown module IDs. Run the
full Python 3.11 and 3.12 CI before treating this round as verified.

## Block 38.4 – explicit expert correction

LocalReviewDraft.correct_ai_finding allows an expert to replace the internal
unverified AI candidate label with a nonempty expert-entered label. The method
only operates on an existing unverified AI candidate and resets that finding's
prior accept/reject decision. The existing report gate still refuses unchanged
unverified labels. LocalReviewedReportController now also compares the reviewed
analysis with its approval snapshot and blocks export after subsequent changes.
No automated model conclusion is promoted to a verified diagnosis.

Limitations: this in-memory workflow is not a durable signed audit trail; user
identity, verified evidence, image geometry and UI integration still require
production implementation. Run Python 3.11/3.12 CI before declaring success.
