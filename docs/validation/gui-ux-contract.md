# SolarCheck shared GUI/UX contract

Status: GUI definition block, step 1/10.

This contract defines the shared operator experience for online and Windows offline
editions. It does not select a concrete UI toolkit or duplicate domain rules.

## Primary workflow

The primary navigation follows the backend workflow:

**Project -> Import -> Processing -> Plant overview -> Review -> Report -> Export**

Online and offline editions use the same terminology, ordering, core interactions,
and status semantics. Deployment-specific concerns belong behind application
services/adapters or in a secondary technical-status area.

## Processing experience

After import, SolarCheck opens a dedicated processing view with a prominent
overall progress indicator and visible stage progression. Expected stages include
image/pair preparation, orthomosaic generation, RGB/thermal registration, module
processing, thermal analysis, finding assignment, and project preparation.

Progress must be truthful:

- show a numeric percentage only when the backend can provide a meaningful
  measured total/current value;
- otherwise show an indeterminate running state;
- where available, show concrete counters such as processed images or modules;
- show the active stage and elapsed time without inventing completion estimates;
- on failure, preserve the last persisted state, explain the failed stage, and
  expose retry only through the backend workflow/action contract.

A transient operation result must never make the UI display a stage as completed
unless the required evidence has actually been persisted.

## Central plant overview

After processing, the primary analysis workspace is the complete PV plant
orthomosaic rather than a table-first view.

The viewer has three independent layers:

1. **RGB base layer** — the visual orthomosaic.
2. **Thermal comparison layer** — the registered thermal orthomosaic.
3. **Analysis overlay** — module geometry, module identity, findings, review
   state, and other non-destructive annotations.

The operator can switch directly between RGB and thermal views. A comparison mode
provides a draggable wipe slider so the same plant region can be inspected across
both modalities.

The comparison control is a visualization aid only. It must not imply validated
pixel-level cross-sensor registration where that provenance has not been
established.

## Navigation and scale

The plant viewer must support large installations without requiring the complete
full-resolution mosaic in memory. The intended interaction model is map/GIS-like:

- pan by dragging;
- zoom by wheel/trackpad and suitable touch gestures where supported;
- double-click or equivalent focused zoom;
- a visible action to return to the complete plant extent;
- automatic focus/zoom when the operator selects a module or finding;
- progressive/tiled image delivery or an equivalent pyramid strategy for large
  mosaics.

The exact tiling implementation is deferred until the image-delivery architecture
is selected, but online and offline editions should preserve the same interaction
model.

## Module and finding interaction

Module outlines are an independent overlay. At suitable zoom levels SolarCheck
may reveal module IDs and finding markers without permanently modifying source
imagery.

Selecting a module opens contextual details while retaining the plant location.
The detail area is expected to expose, where available, RGB and thermal crops,
physical module identity, validated thermal measurements/provenance, machine
recommendation, and authoritative human review state.

A finding selection should focus the corresponding module in the plant viewer.
A filter for findings/review-relevant modules should allow the operator to reduce
visual clutter while preserving access to the complete plant.

## Layout direction

The target shell is desktop-oriented and image-first:

- persistent primary navigation on the left;
- project and operational status in the top area;
- large central image/plant workspace;
- contextual details on the right when an object is selected.

Tables remain useful for sorting, filtering, batch navigation, and audit work, but
they supplement rather than replace the spatial plant view.

Exact colors, typography, dimensions, icons, component library, and PySide6/web
implementation are deliberately deferred to subsequent GUI-definition steps.


## Plant viewer interaction contract

The plant overview opens with the complete plant extent visible. Changing between
RGB, thermal, and comparison modes preserves the same viewport, center, and zoom
so the operator never has to relocate the inspected area.

### RGB/thermal comparison wipe

Comparison mode uses a vertical wipe boundary. Its grab handle is visually hinted
at on the **right edge of the plant workspace** when comparison is available, so
the control is discoverable without permanently covering the imagery.

The intended gesture is to grab the right-edge handle and drag it **from right to
left** across the plant. This progressively reveals the comparison layer while
leaving the opposite modality visible on the other side of the boundary. The
boundary remains draggable in both directions after activation.

The handle must have a clear RGB/thermal comparison cue and a sufficiently large
hit target. It should not conflict with the contextual detail panel: the wipe
belongs to the image workspace edge, while the detail panel is a separate layout
region. Keyboard-accessible adjustment must be provided in addition to pointer
dragging.

The initial side assignment (RGB base versus thermal reveal) should remain
consistent throughout the product and be labelled in the viewer; it must not be
inferred from color alone.

### Viewer controls

A compact control group overlays or borders the image workspace without obscuring
inspection content. It provides:

- RGB, Thermal, and Compare view modes;
- zoom in/out;
- fit complete plant extent;
- optional reset to the last overview viewport;
- layer visibility for module outlines, module IDs, findings, and review state;
- a review-relevant/findings-only filter.

Pan and zoom remain available while comparison mode is active. Moving or zooming
the viewport moves both image modalities and all overlays together; the wipe
position is a screen-space comparison control and must not desynchronize the
underlying spatial registration.

### Selection and contextual details

Selecting a module or finding keeps the central plant viewer visible and opens
the contextual detail region on the right. The selected geometry is highlighted
without modifying the underlying RGB or thermal source.

Selection from a list or finding marker focuses the corresponding module at a
useful inspection zoom while preserving a one-action route back to the complete
plant extent. Closing the detail region must not reset the current viewport.

The right detail region may be resized or collapsed to maximize imagery. Its
presence must not move the comparison handle out of the image workspace or make
the wipe ambiguous.

### Visual-density behavior

At plant overview scale, prioritize plant shape, major findings, and orientation.
At intermediate zoom, reveal module outlines and finding markers. At detailed
zoom, module IDs and precise selection geometry may appear. This progressive
detail avoids covering large plants with unreadable labels.

Exact zoom thresholds are implementation details and should be validated with
representative small, medium, and large PV installations before being fixed.


## Module and finding interaction contract

Selecting a module in the plant viewer opens a compact **finding box** in the
contextual detail region. The map remains the primary workspace; selection must
not replace the plant view with a separate full-screen record.

The finding box is intentionally concise. It should answer at a glance:

- which physical module is selected;
- whether a finding exists and its review state;
- a short, coarse finding indication where available;
- the most relevant validated thermal value(s), with provenance/status made
  visible when necessary;
- whether human review is still required.

The GUI must distinguish a machine-generated recommendation from an authoritative
human review. A recommendation must not be styled as a confirmed diagnosis.

The finding box provides an explicit **More in report** / **Report details**
action. Detailed evidence, longer finding descriptions, provenance, supporting
images, and report-oriented documentation belong in the report/detail workflow
rather than overcrowding the plant overview.

If no confirmed finding exists, the box must say so plainly rather than inventing
a diagnosis. Unclear findings remain visibly unclear and review-relevant.

### Review actions

Where the backend permits review, the contextual box exposes the authoritative
human decisions **Confirm**, **Unclear**, and **Reject**. Their availability is
derived from backend state and permissions, not duplicated in widget logic.

After a review action, the viewer refreshes from persisted state. The module
marker, finding box, counters, and filters must therefore reflect the saved
review result rather than an optimistic UI-only state.

### Fast inspection flow

The operator can move to the previous/next review-relevant module without
returning to a table. Selecting an item from a findings list focuses that module
and opens the same finding box, so map navigation and list navigation converge on
one detail interaction.

The compact box should remain usable while RGB/thermal comparison is active.
Opening it must not reset zoom, pan position, selected module, or comparison wipe
position.


## Processing and recovery interaction contract

After import, SolarCheck opens a dedicated processing view. It communicates both
the overall workflow position and the currently active processing operation
without inventing progress.

### Progress presentation

Where the backend exposes a meaningful total/current measure, the GUI may show a
determinate percentage and concrete counter (for example processed images or
modules). Where no trustworthy measure exists, the active stage uses an
indeterminate activity indicator instead of a simulated percentage.

The view distinguishes:

- overall processing progress when it can be derived reliably;
- the active processing stage;
- stage-specific counters when available;
- elapsed runtime;
- completed stages backed by persisted evidence;
- blocked, failed, or interrupted stages with a human-readable reason.

A lack of percentage movement alone is not evidence that processing is stuck.
Long-running stages may legitimately remain at one visible percentage.

### Activity and interruption detection

Long-running workers should expose a heartbeat or equivalent activity signal when
the execution architecture supports it. Loss of that signal may cause the GUI to
show **No activity detected — check processing**, but must not automatically mark
the operation as failed solely because progress has not changed.

After application/OS restart, opening the project re-derives workflow state from
persisted evidence. If processing was interrupted, the GUI offers recovery from
the last valid persisted boundary rather than claiming that the interrupted stage
completed.

### Recovery actions

SolarCheck distinguishes three recovery actions:

1. **Continue** — preferred normal recovery. Re-derive persisted state and resume
   from the next required processing boundary.
2. **Retry step** — rerun the failed/interrupted processing stage and invalidate
   only downstream derived results whose validity depends on that stage.
3. **Restart processing** — explicit maintenance/recovery action that rebuilds
   derived processing results from the preserved import/source data.

These actions must not be interchangeable labels for the same destructive
operation. Their exact invalidation scopes are defined per concrete processing
stage before implementation.

Imported source data must not be silently deleted by processing recovery. Human
review decisions must also not be silently discarded. If a future dependency
requires invalidating reviewed evidence, SolarCheck must block the restart and
require an explicit, separately specified migration/review workflow rather than
quietly resetting it.

### Restart safety

**Restart processing** requires confirmation that explains exactly which derived
artifacts will be removed/rebuilt and which source/review data will remain.
Generic warnings such as “data may be lost” are insufficient.

Recovery commands pass through the same application workflow/action boundary as
normal operations. A button press does not optimistically advance the progress
display; after the operation SolarCheck reloads the persisted state and renders
that result.

The implementation must not claim transactional or resumable behavior for a
processing stage until that stage's persistence/invalidation behavior has been
tested explicitly.


## Project start and guided creation contract

The start screen favors a small number of clear next actions over exposing the
whole application at once.

A prominent **Create new project** action starts the normal workflow. The operator
first enters the project name and the project is persisted immediately so a
stable project context exists even if image selection is cancelled or the
application closes.

### Plant/report data during project creation

Project creation also asks the operator to enter the plant and inspection data
needed for the eventual report. The form must clearly distinguish:

- data required to create/save the project;
- report-relevant data that is still incomplete;
- optional information.

The operator may save an incomplete project where domain rules permit it, but
SolarCheck keeps the missing report data visible as an explicit completeness
state and prompts the operator to complete it before report readiness/release.
Missing information must not be silently replaced with invented defaults.

The exact field set is derived from the existing report/domain model before the
form is implemented, so the GUI does not create a second incompatible report
schema.

### Guided first-run actions

After the project is saved, the primary next action is **Import images**. The
operator may select the complete inspection image set together; SolarCheck is
responsible for identifying supported RGB/thermal inputs and performing the
available pairing/import logic rather than requiring separate RGB and thermal
import workflows.

After import, the screen shows a concise persisted import summary such as RGB
frames, thermal frames, recognized pairs, failures, and items requiring
attention. Counts must come from backend/import results or persisted queries.

When processing prerequisites are satisfied, the next prominent action becomes
**Start processing**. If processing is blocked, the action remains visible but
disabled and the backend-derived blocker is shown next to it rather than hiding
the workflow.

### Existing projects and resumption

Existing projects appear in a compact list/card view with project name, recent
activity where available, and backend-derived workflow state. Selecting a project
opens its safe resume point: import, processing/recovery, review, report, or
export as appropriate.

Interrupted processing is shown as recoverable work rather than as completed.
Projects with incomplete plant/report data retain a visible reminder even if
image processing can otherwise continue.

The guiding UX principle is: **show the next meaningful primary action, while
keeping incomplete prerequisites and blockers explicit.**


## Project and plant data form contract

The project-creation form groups operator-entered data by purpose and keeps
automatically derived inspection metadata out of the initial manual form.

### Required operator-entered fields

The following information is required for the project/report data set:

**Executing company**
- company name;
- postal address;
- contact details.

**Responsible person**
- name of the responsible person for the inspection/report.

**PV plant**
- plant name;
- plant postal address;
- plant operator / owner organization or person.

These fields must be visibly marked as required and validated before the project
is considered complete for reporting. The UI may preserve a draft project while
data is incomplete, but must retain an explicit incomplete-data state.

### Optional operator-entered fields

The following plant-operator details are optional:

- operator contact person;
- operator contact details.

Optional fields remain editable later and must not block image import or
processing merely because they are empty.

### Inspection metadata derived from imagery

Inspection date, time, and precise GPS positions are expected to be derived from
the imported image metadata where trustworthy values are available. They are not
duplicated as mandatory manual fields during initial project creation.

Automatically derived metadata must preserve its source/provenance. SolarCheck
must not silently manufacture a date, time, or GPS position when source metadata
is missing, invalid, inconsistent, or unavailable.

After import, the project data view should show the detected inspection
date/time/location information for operator verification. Missing or conflicting
metadata becomes an explicit review item. Any future manual correction/override
must be stored as such and remain distinguishable from the original image-derived
metadata.

### Form layout

To keep project creation simple, the form should use three visible sections:
**Executing company**, **Plant**, and **Operator/contact**. The responsible person
belongs with the executing-company/inspection context.

The primary action is **Save project and continue**. Once saved, the guided flow
moves to **Import images**. Report-data completeness remains visible from the
project header/status area so it can be corrected later without repeating project
creation.


## Image import interaction contract

After project creation, the guided primary action opens **Import images**. The
import screen accepts the complete inspection image set together; the operator
does not need separate RGB and thermal import workflows.

### Source selection

The main surface is a large, clear file drop/select area with:

- **Select images** for explicit multi-file selection;
- **Select folder** for a complete inspection directory;
- drag-and-drop where supported by the platform.

Online and offline editions should preserve the same conceptual interaction even
if browser and desktop file-selection mechanics differ.

Selection itself does not imply successful import. SolarCheck validates supported
inputs and persists accepted evidence through the import/application boundary.

### Recognition and import summary

After import, show a concise summary sourced from import results/persisted data,
for example:

**652 images · 326 RGB · 326 thermal · 324 pairs · 4 items need attention**

The exact categories are shown only when the backend can support them. Technical
details stay collapsed by default; an **Items needing attention** area exposes
unsupported files, parse failures, missing counterparts, or other actionable
issues without overwhelming the normal path.

Unpaired imagery is not silently discarded. The UI must distinguish accepted but
unpaired evidence from files that failed import.

### Inspection metadata verification

After accepted imagery is persisted, show the inspection metadata derived from
the image set for operator verification:

- detected date/time range;
- GPS availability/coverage;
- missing or conflicting metadata warnings.

Do not reduce a multi-image inspection to one invented timestamp or coordinate.
The project/report layer may derive a suitable summary only according to an
explicit domain rule. Source metadata and provenance remain authoritative.

### Transition to processing

When backend prerequisites are satisfied, **Start processing** becomes the
prominent next action. Its enabled/blocked state is derived from the application
workflow contract.

If processing cannot start, keep the action visible and explain the blocker next
to it. Issues that do not invalidate processing may remain warnings and must not
be promoted to blockers without a domain rule.

Starting processing uses the same guarded application-service execution path as
other workflow actions. The UI then moves to the processing/progress view and
does not mark processing complete until persisted evidence supports that state.

### Re-entry

Reopening the import screen for an existing project shows the persisted import
summary rather than an empty picker. Adding/re-importing imagery must be treated
as an explicit operation with defined downstream invalidation behavior before it
is enabled for processed/reviewed projects; the GUI must not silently mix new
source imagery into an already reviewed result.


## Optional geospatial background contract

The plant viewer may show a georeferenced map/satellite background beneath the
inspection orthomosaic to improve operator orientation in the surrounding site.

The visual stack is:

1. **Optional map/satellite background** — orientation only.
2. **RGB orthomosaic** — inspection visual evidence.
3. **Thermal comparison layer** — registered inspection thermal imagery.
4. **Analysis overlay** — modules, findings, identities, and review state.

The background is never inspection evidence and must not become a prerequisite
for import, processing, review, reporting, or export.

### Offline behavior

SolarCheck's Windows offline edition must remain fully usable without an Internet
connection. If no permitted local/cached background is available, the background
layer is simply omitted and the inspection orthomosaic is shown against a neutral
viewer background. This condition is not an error and must not block the
workflow.

The UI may expose a **Background map** layer toggle only when a usable source is
available. It should not repeatedly prompt for connectivity during normal offline
inspection work.

Online map/satellite retrieval and any optional caching/offline packaging are
separate adapter concerns. A concrete provider must not be embedded into the
shared UX contract until its API terms, attribution requirements, licensing, and
offline/cache rights have been reviewed.

### Registration and transparency

Where a background is available, its placement uses the project's geospatial
reference. The viewer may provide orthomosaic opacity control to help the
operator visually orient the plant against surrounding buildings, roads, and
terrain.

This visual comparison does not replace registration validation. A map
background must not be used to claim inspection-coordinate accuracy beyond the
validated project georeferencing.


## Review workspace contract

The primary review experience combines a report-like, vertically scrollable
**review stream** with the synchronized plant viewer. It is not a flat list of
every detected module.

By default, the stream prioritizes modules/findings that actually require human
attention: machine-proposed findings, unclear cases, unresolved identity/evidence
issues, and other backend-defined review requirements. Unremarkable modules do
not flood the default review queue, but remain accessible through the plant view
or explicit filters.

### Review cards

Each review-relevant item is represented by a compact card that may contain:

- physical module identity / location reference;
- short finding indication and current review state;
- RGB crop and thermal crop where available;
- relevant validated thermal measurement(s);
- clearly labelled machine recommendation where present;
- optional concise reviewer note;
- authoritative **Confirm**, **Unclear**, and **Reject** actions where permitted;
- **Report details** for the deeper evidence/report context.

Cards must not imply a confirmed diagnosis from machine output. Missing source
imagery or unvalidated measurements remain visibly unavailable rather than being
substituted.

### Synchronized spatial context

The review stream and plant viewer are bidirectionally synchronized.

When a review card becomes the active item, the corresponding module is
highlighted/focused in the plant viewer. Selecting a review-relevant module or
finding in the plant viewer activates and scrolls to the corresponding review
card.

This synchronization must preserve RGB/thermal mode, comparison wipe position,
and useful viewport context unless the operator explicitly requests a reset.

### Review progress and filters

A persistent review summary shows backend-derived counts such as:

**To review · Confirmed · Unclear · Rejected**

Filters allow the operator to view open/review-required items, confirmed items,
unclear items, rejected items, or all findings. Counts and filters reflect
persisted review state rather than optimistic UI state.

The default queue must remain scalable for large plants. It should not render
thousands of heavy image cards simultaneously; virtualized/lazy card rendering
or an equivalent strategy is expected.

### Focus mode

A review card can enter **Focus mode** for difficult cases. Focus mode gives the
selected RGB/thermal evidence substantially more screen area while retaining the
same review decision controls and a direct **Previous / Next review item**
navigation.

Leaving Focus mode returns to the same position in the review stream and plant
context. Review decisions persist through the backend before counters, filters,
or navigation treat an item as completed.

### Relationship to the report

The review stream deliberately resembles a concise inspection report so the
operator can read findings naturally from top to bottom. It is nevertheless a
review workspace, not a second report renderer.

The final report is assembled from the authoritative persisted review/evidence
model. Detailed narrative, complete provenance, report formatting, and released
document content remain responsibilities of the report workflow.


## Report, export, and application-menu contract

When the persisted workflow confirms that the required processing and review
prerequisites are complete, the primary workspace exposes prominent **Report**
and **Export** actions. Their availability is derived from backend readiness and
release rules; the GUI must not enable them merely because processing appears
visually finished.

If an action is not yet available, it remains discoverable in a disabled state
with the concrete blocker, for example incomplete review or missing required
report/project data.

### Report action

**Report** opens the report workflow/preview built from the authoritative
persisted report/evidence model. It is the place for the detailed finding
narrative, evidence, provenance, plant/operator information, and report-oriented
review before release.

The report screen must distinguish draft/reviewed/released semantics according to
the existing report contract rather than treating document preview as release.

### Export action

**Export** opens the available output choices supported by the backend report
export contract. Format choices are not duplicated as UI-only capabilities.
Export/release actions remain fail-closed when their corresponding backend gate
is not satisfied.

### Familiar top application menus

In addition to contextual buttons and the persistent workflow navigation, all
applicable user commands should also be reachable through familiar drop-down
menus in the page/window header. This provides a conventional secondary access
path for users who expect desktop-style application menus.

The initial menu information architecture is:

- **Project** — new/open project, project/plant data, image import, close project;
- **Processing** — start/continue processing and permitted recovery operations;
- **View** — RGB, thermal, comparison, zoom/fit, layer visibility, optional
  background map, detail/focus presentation;
- **Review** — review filters/navigation and permitted review actions;
- **Report** — open report, report details/readiness;
- **Export** — available export operations;
- **Help** — user guide, application/version information, and later support or
  diagnostics entry points.

A command exposed in more than one place must call the same application action
and obey the same enabled/blocked state. Menus are alternate navigation, not a
second implementation of workflow logic.

Unavailable commands should normally remain visible but disabled where doing so
helps users understand the workflow. The UI should provide the blocker through
tooltip/status/help text rather than silently hiding expected functions.

Exact menu wording may be localized, but command meaning and ordering should stay
consistent between online and offline editions. Platform conventions may adjust
presentation without changing the underlying command model.
