# Phase 10 plan: application integration and workflow readiness

Phase 10 closes the gap between the tested domain/report components and a coherent application workflow. It does not redesign the scientific models or reopen the Phase 9 report contract.

## Current integration baseline

The repository already contains dedicated packages for M3T import and persistence, RGB/thermal pairing and registration, PV-module detection and identity, finding localization/prioritization, human review/model governance, and report assembly/export.

The existing application service `services/project_pipeline.py` currently integrates only the first ingestion slice: M3T import, pairing, thermal candidate generation and SQLite persistence. Later module-detection, review and report stages are implemented as separate tested components rather than one explicit application workflow.

No GUI package is currently present under `src/mcm_solarcheck`. PySide6 is therefore treated as a future presentation layer over application services, not as a place to duplicate domain decisions.

## Phase 10 objective

Define and validate explicit application-level workflow state and orchestration from an existing/imported project through processing, review readiness and report readiness. The workflow must expose why a next step is or is not available and must preserve the fail-closed review/release rules already established.

## Acceptance gates

1. Inventory the existing stage boundaries and persisted prerequisites.
2. Define backend-neutral workflow stages/status without GUI dependencies.
3. Derive stage readiness from persisted project evidence rather than mutable UI flags.
4. Keep machine classification advisory and human review authoritative.
5. Prevent report-release readiness while unresolved review or physical-module identity gates remain.
6. Provide application services that a CLI or future PySide6 GUI can call without embedding domain logic in widgets.
7. Make failures/retry states explicit enough for safe project resumption.
8. Add integration tests across meaningful stage transitions and blocked transitions.
9. Document the GUI information architecture only after the backend workflow contract is stable.
10. Finish with a green end-to-end Phase 10 close-out gate before starting GUI implementation.

## Non-goals

Phase 10 does not change model scientific validation, claim licensed-standard conformity, implement commerce/pricing, or build the automatic flight planner. It also does not allow the GUI to bypass review, provenance or release gates.

## GUI follow-on

The later PySide6 GUI should map the backend workflow into clear project navigation: project/import, processing, findings/review, report and export. Progress indicators and action availability must be derived from backend state. GUI convenience actions may trigger application services, but widgets must not become an independent source of inspection truth.


## GUI information architecture contract

The online and Windows offline editions should present the same primary workflow,
terminology, navigation order, status semantics, and action placement. Deployment
differences must be isolated behind application services and adapters rather than
creating separate user workflows.

The shared primary navigation follows the persisted workflow:

1. **Project** — project identity, inspection context, and project selection.
2. **Import** — source selection, import progress, failures, and retry.
3. **Processing** — pairing, thermal processing, module/finding processing, and
   persisted processing status.
4. **Review** — findings, evidence, physical module identity, and authoritative
   human review.
5. **Report** — report preview/readiness and explicit release blockers.
6. **Export** — available report outputs and completed export results.

Each screen must derive action availability and blockers from
`ProjectWorkflowState` / `WorkflowAction`; widgets must not recreate domain
rules. Failed operations remain retryable and must not visually advance a stage
unless the required evidence was persisted.

Online/offline differences may cover storage adapters, authentication or account
integration, update delivery, connectivity indicators, and resource locations.
They should not change the inspection vocabulary or the operator's core sequence.
An offline-only technical status area may expose local database, model/resource,
and update state without altering the shared workflow.

Detailed visual design (layout, component hierarchy, typography, iconography,
responsive behavior, dialogs, and exact desktop/web shell) is intentionally left
for the dedicated GUI-definition step after this backend contract is closed.


## Phase 10 integration checkpoint — steps 11–20

The second ten-step block closes with the application boundary ready for GUI
definition:

- workflow actions are fail-closed and derive availability from persisted state;
- `ProjectApplicationService` provides one guard boundary for callers;
- execution is ordered as guard -> operation -> persisted evidence -> re-derived
  workflow state;
- transient success/failure attempts do not replace persisted workflow evidence;
- blocked operations are rejected before caller side effects;
- retry behavior is tested so failures do not create artificial progress;
- online and offline editions share one operator workflow and GUI information
  architecture contract.

This checkpoint does **not** claim transactional atomicity for every existing
multi-write pipeline operation. Concrete operations must be integrated and tested
individually before such a guarantee is made.

The next GUI-definition block may specify the shared visual shell, navigation,
screen layouts, component states, and interaction patterns. It must continue to
consume the backend workflow/action contract rather than duplicate its rules.
PySide6 implementation and web/online implementation choices remain downstream
of that shared UX definition.

Phase 9 reporting remains frozen. Scientific production-model validation,
licensed standards conformity review, pricing/flight-planner work, and the
Windows installer release branch remain separate gates/workstreams.
