# Phase 9 plan: inspection report pipeline

Phase 9 turns reviewed project evidence into a stable, editable customer report without coupling report semantics to DOCX, ODT or PDF layout code.

## Report structure

1. Cover page: MCM-Dronetech GmbH branding, MCM-SolarCheck banner, contact data, customer/site identity, inspection date and report/project ID.
2. One-page inspection overview where practical: customer/site data, date/time, irradiance summary with explicit source/provenance, total inspected PV modules, counts of conspicuous and manual-review modules, RGB site overview and thermal site overview.
3. Detail section: only modules with reviewed findings or an explicit manual-inspection requirement. Each module block carries module ID, finding description/status and paired RGB/thermal module imagery where available.
4. Closing review summary: inspected/without documented finding/conspicuous/manual-review counts, inspector, inspection date, equipment/data provenance and release status.

## Architecture and acceptance gates

- Introduce a backend-neutral `InspectionReport` model before document rendering.
- Human-reviewed findings are authoritative. Machine classifications remain suggestions and must never silently become confirmed defects.
- Physical module identity is the service target. Optional GPS/RTK is supplemental evidence; no synthetic hotspot GPS coordinate is generated.
- Celsius and delta-temperature values are emitted only with validated calibrated-temperature provenance.
- Irradiance values require a named source/provenance; derived or missing values must not be presented as directly measured facts.
- RGB and thermal remain separate modalities linked through module/ImagePair identity.
- Report generation must be deterministic from the same reviewed report model.
- DOCX and ODT are editable outputs; PDF is a rendered/final output derived from the same report semantics.
- Layout/branding is kept separate from inspection logic so templates can evolve without changing finding semantics.
- Norm wording is conservative until the licensed DIN IEC/TS 62446-3 (VDE V 0126-23-3):2018-04 reporting requirements have been checked. Do not claim full conformity from public metadata alone.

## First implementation slice

Build and validate the neutral report model: project/customer identity, inspection metadata, irradiance provenance, aggregate module counts, overview-image references, reviewed module-detail blocks, equipment/provenance and report release state. Renderer-specific code follows only after this contract is tested.

## Non-goals

Phase 9 will not fabricate missing measurement values, promote unreviewed AI output into customer findings, infer electrical root causes, create absolute hotspot GPS positions, or embed satellite/basemap imagery in the report.
