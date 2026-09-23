# Phase 6 localization and prioritization contract

Phase 6 uses the physical PV module as the service location for a finding. A hotspot pixel is not projected to an invented absolute GPS coordinate.

## Localization

- `module_id` is the primary repair reference.
- Frame GPS/RTK is optional provenance and orientation evidence.
- Missing GPS does not invalidate an otherwise resolved physical module.
- Invalid or non-finite GPS coordinates are omitted rather than propagated.
- Frame GPS alone never creates a module assignment.
- Cross-sensor module assignment still requires validated, unambiguous geometry.

## Prioritization

Prioritization is an expert-review ordering aid, not an automatic defect classification. Raw DJI radiometric values are never interpreted as Celsius or thermal severity. Without calibrated temperature evidence and valid confidence, a finding remains `unrated`. With calibrated evidence it may enter the `review` queue; no thermal defect threshold is inferred by Phase 6.

Equal-priority findings are ordered deterministically by finding ID for reproducible review and reporting.

## Reporting

Confirmed evidence names the physical module when available and may include valid GPS coordinates as supplementary information. GPS is not required when the module is known. Missing or invalid optional GPS is rendered as unavailable rather than estimated.

This keeps the operational workflow aligned with module replacement: identify the affected module, retain auditable source evidence, and leave the final finding decision to expert review.
