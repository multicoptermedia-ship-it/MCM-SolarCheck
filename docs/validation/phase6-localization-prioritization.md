# Phase 6 localization and prioritization contract

Phase 6 uses the physical PV module as the service location for a finding. A hotspot pixel is not projected to an invented absolute GPS coordinate.

## Localization

- `module_id` is the primary repair reference.
- `service_location_status` is derived from module identity and cannot be promoted by GPS alone.
- Frame GPS/RTK is optional provenance and orientation evidence.
- Missing GPS does not invalidate an otherwise resolved physical module.
- Invalid or non-finite GPS coordinates are omitted rather than propagated.
- Frame GPS alone never creates a module assignment.
- Cross-sensor module assignment still requires validated, unambiguous geometry.
- Image-evidence planning carries the same resolved/unresolved module contract.

## Prioritization

Prioritization is an expert-review ordering aid, not an automatic defect classification. Raw DJI radiometric values are never interpreted as Celsius or thermal severity.

A numeric `temperature_c` value is not sufficient proof of calibration. Review priority requires explicit persisted provenance: `temperature_status=calibrated`, a non-empty `temperature_provider`, finite Celsius evidence, and valid confidence. Missing or inconsistent provenance fails closed to `unrated`. Even with validated calibrated evidence, Phase 6 only permits review ordering; it does not infer a thermal defect threshold or severity class.

Equal-priority findings are ordered deterministically by finding ID for reproducible review and reporting. Human review remains the final finding decision.

## Reporting

Confirmed evidence names the physical module when available and may include valid frame GPS coordinates as supplementary information. GPS is not required when the module is known. Missing or invalid optional GPS is rendered as unavailable rather than estimated. Reports explicitly warn when a confirmed finding has no resolved physical module.

Temperature validation in report data uses the same provenance rule as prioritization. A Celsius number without explicit calibration provenance must not produce a validated-temperature statement or review-priority promotion.

## Closure regression

`tests/test_phase6_contract.py` exercises the Phase 6 contract end to end across query records, report modeling, and image-evidence planning:

- valid frame GPS never substitutes for physical module identity;
- unproven numeric Celsius never promotes review priority;
- explicit calibration provenance permits review ordering without creating a severity claim.

CI run #309 on commit `d5eb70da451ea018af14928c7853ca4ec09fffda` passed this closure regression on the project test matrix. The preceding mixed-provenance regression commit `472e25cd72393474440e156da6cdfb55d3fed4ea` is also part of the tested branch history.

This keeps the operational workflow aligned with module replacement: identify the affected module, retain auditable source evidence, order review conservatively, and leave the final finding decision to expert review.
