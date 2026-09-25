# SolarCheck visual design system

Status: Design contract for GUI implementation. This document refines visual
presentation only; it does not redefine workflow, review, report, or release
semantics.

## 1. Visual foundation

SolarCheck uses a restrained technical/corporate visual language aligned with
the MCM SolarCheck identity.

### Palette roles

- **Anthracite**: primary navigation, application header, high-contrast chrome.
- **Light neutral**: main work surface, forms, review stream, report surfaces.
- **MCM/SolarCheck green**: brand accent, selected navigation, primary actions,
  focus accents, and positive non-thermal UI emphasis.
- **Neutral greys**: borders, disabled controls, secondary metadata, separators.
- **Thermal palette**: reserved for thermal imagery, legends, and measured
  thermal evidence; it is not a general decorative UI palette.
- **Semantic states**: review/blocker/success states must use icon/text together
  with color and remain distinguishable without color.

Exact production color values must be taken from approved MCM brand assets or a
documented UI token set before implementation; screenshots or generated artwork
are not a reliable source for sampling brand colors.

### Typography

Use a modern, highly legible sans-serif system suitable for dense technical
interfaces. Prefer platform/system fonts unless an approved redistributable MCM
typeface is explicitly supplied.

Hierarchy:
- application/project title: strong but compact;
- screen title: clear visual anchor;
- section/card title: medium emphasis;
- body/control text: optimized for sustained desktop use;
- metadata: smaller but never dependent on low contrast.

The UI must remain usable at common Windows display scaling levels; component
sizes are not tuned to a single screenshot resolution.

### Geometry and density

Use moderate corner radii and restrained shadows. Technical image workspaces
should feel precise rather than decorative. Controls use consistent spacing and
minimum hit areas suitable for mouse and touchpad use.

Image evidence receives the largest share of the workspace. Toolbars and panels
should not consume permanent space unless they provide current-task value.

## 2. Core component language

Primary buttons use the brand accent and are limited to the next meaningful
action. Secondary actions use neutral styling. Destructive/rebuild actions must
not visually resemble the normal primary path.

Disabled actions remain legible and expose their blocker through nearby status,
tooltip, or contextual explanation.

Cards are used for projects, review findings, and concise summaries. They should
share spacing, heading, metadata, and action placement so users learn one visual
grammar.

Status chips/badges are compact secondary indicators only; authoritative state
must also be stated in text where the distinction matters.

Menus, contextual buttons, keyboard commands, and persistent navigation map to
the same command model and therefore share labels/icons where practical.

## 3. Shell dimensions and behavior

Desktop baseline:
- compact dark header with conventional drop-down application menus and current
  project/status context;
- persistent dark left workflow navigation;
- flexible center workspace;
- optional resizable/collapsible right contextual panel.

The center workspace expands when the right panel is collapsed. The plant viewer
must not reset zoom, center, comparison wipe, or selection merely because a
panel opens/closes.

At narrower supported widths, secondary labels may collapse before primary
inspection imagery is reduced below a useful size. Exact responsive breakpoints
belong to implementation testing.

## 4. Accessibility and evidence integrity

Target WCAG-style readable contrast for normal interface text and controls even
where the desktop framework is not a web browser.

Keyboard focus must be visible. The RGB/thermal wipe handle, menus, navigation,
review actions, and major viewer controls require keyboard-accessible paths.

Icons never replace essential wording for review/release decisions. Tooltips may
explain controls but must not carry the only copy of critical information.

Visual overlays must not alter or obscure source evidence in a way that could be
mistaken for the underlying image. Users can hide analysis overlays and inspect
the RGB/thermal source presentation.

## 5. Splash-screen visual direction

The application splash uses the approved MCM/SolarCheck corporate direction:
MCM logo/wordmark, **MCM-Solar-Check**, drone imagery, PV imagery, and a
thermal-inspection motif on a clean photographic background.

Advertising copy, website promotion, marketing benefit icons, and unrelated
sales text are omitted from the application splash.

A dark translucent lower status region may carry a restrained brand-green
activity/progress indicator and truthful startup text. A numeric percentage is
shown only if startup progress is actually measurable.

The splash closes as soon as initialization permits the application shell to
become usable; it never enforces a marketing delay.

## 6. Design token implementation boundary

Before production GUI code hard-codes styling, the implementation should define
central reusable tokens for:
- brand/accent and neutral color roles;
- semantic status roles;
- spacing scale;
- corner radii;
- typography sizes/weights;
- control heights and icon sizes;
- panel/header/navigation dimensions.

Components consume those tokens rather than scattering literal values. This
keeps online/offline presentation aligned and makes later approved corporate
design adjustments low-risk.


## 7. Application shell specification

The shared application shell is the stable visual frame around every SolarCheck
workflow screen. It must make the current project, current workflow location,
available commands, and backend-derived status understandable without competing
with inspection imagery.

### Header

The dark header is compact and divided into three functional zones:

1. **Brand/application zone** — compact MCM SolarCheck identity; selecting it may
   return to the project/start workspace but must not discard unsaved form edits
   without the normal guard.
2. **Application menu zone** — conventional drop-down menus **Project**,
   **Processing**, **View**, **Review**, **Report**, **Export**, and **Help**.
3. **Project/status zone** — current project name plus concise persisted workflow
   status. A status indicator opens explanatory detail rather than relying on
   color alone.

Long project names truncate visually without changing the stored name; the full
name remains discoverable.

### Left workflow navigation

The persistent dark navigation follows the defined workflow order:

**Project · Import · Processing · Plant · Review · Report · Export**

Each entry has a consistent icon, text label, and state treatment. The navigation
shows where the user is and which later areas are blocked/available, but it does
not invent completion flags.

Navigation entries should remain visible even when blocked. Selecting a blocked
destination explains the prerequisite instead of silently doing nothing or
bypassing the backend gate.

The active item uses the MCM/SolarCheck accent sparingly. Completed stages use a
quiet confirmation treatment; unresolved/review-required stages use explicit
icon/text semantics.

### Center workspace

Every screen begins with a compact page header containing:
- page title;
- optional one-line task/status explanation;
- the single primary next action when one exists.

The remainder is task-specific. Forms use a readable bounded content width;
plant/review image workspaces expand to use available space.

Global commands do not need to be repeated as large page buttons unless they are
the meaningful next action for the current workflow.

### Right contextual panel

The right panel is contextual rather than globally permanent. It is used for
selected module/finding details, layer controls when appropriate, metadata, and
other current-object information.

It is resizable and collapsible. Opening, resizing, or closing it must preserve
viewer state and selection. When no contextual object exists, the workspace
should reclaim the space instead of displaying an empty decorative panel.

### Status and blocker presentation

Use three levels of feedback:
- compact global/project status in the header;
- stage-specific readiness/blocker near the page title or primary action;
- detailed explanation adjacent to the affected control when user action is
  required.

Routine status should not be shown as modal dialogs. Modal dialogs are reserved
for consequential confirmation, such as a processing rebuild with explicit
invalidation consequences.

### Header-menu and page-action parity

A command appearing in a header menu and as a contextual button uses the same
label, icon where practical, enabled state, shortcut, and application-service
action.

This parity is part of the design contract and should be testable through a
central command/action registry rather than duplicated widget callbacks.

### Initial desktop proportions

The implementation may tune values through design tokens and usability testing,
but the starting proportions are:
- header: compact single-row application chrome;
- left navigation: narrow enough to preserve imagery, wide enough for full
  German workflow labels;
- center: dominant flexible region;
- right detail panel: approximately one quarter of a typical desktop workspace,
  user-resizable with sensible minimum/maximum widths.

No fixed pixel values in this document constitute release requirements. Windows
display scaling and representative laptop/desktop resolutions must be tested
before dimensions are frozen.


## 8. Start and project workspace

The first usable screen after startup is deliberately calm. It helps the user
either create a new inspection project or safely resume an existing one without
presenting the full technical workspace before a project context exists.

### Start-screen hierarchy

The normal application header remains available. The center workspace contains:

1. a concise **SolarCheck / PV inspection** heading;
2. a prominent primary action **Create new project**;
3. a **Recent/existing projects** region;
4. optional compact guidance for first use, linked to the user guide rather than
   marketing copy.

Do not repeat the splash artwork as a large decorative hero. The splash provides
brand recognition during initialization; the start workspace prioritizes work.

### New-project action

**Create new project** is the single visually dominant action when no project is
open. It uses the brand accent and opens the guided project-data form defined by
the GUI/UX contract.

The form visually groups:
- **Executing company**;
- **PV plant**;
- **Operator/contact**.

Required, report-relevant incomplete, and optional fields are visually distinct
without using alarm styling for ordinary incompleteness. Inline validation is
preferred to error modals.

The primary form action is **Save project and continue**. After persistence, the
shell updates to the new project context and the next primary action becomes
**Import images**.

### Existing-project cards

Existing/recent projects are shown as restrained cards or rows optimized for
scanning. Each item may show only persisted information that is useful for
resuming work:
- project/plant name;
- last persisted activity timestamp if available;
- current safe workflow/resume point;
- concise open-review/blocker information when available.

Do not invent module/image/finding counts merely to make a card look richer.
Counts appear only when the backend can provide them reliably.

Opening a project routes to its backend-derived safe resume point rather than a
hard-coded screen. A user may still navigate to other permitted areas through
the normal shell.

### Empty state

If no existing project is available, show a clean empty state with
**Create new project** and a short sentence explaining the inspection workflow.
Avoid sample/fake projects in production.

### Project-card visual language

Cards use the same neutral surface, typography, status chips, and spacing tokens
as later review/report cards. The project name is the primary visual anchor;
workflow state is secondary.

Hover/selection feedback is subtle. The entire appropriate card region may be
clickable, while destructive project-management actions remain separate and
cannot be triggered by opening the card.

### Returning to the start workspace

Selecting the compact SolarCheck brand/home affordance or the appropriate
**Project** menu command may return to the project workspace. If a form contains
unsaved edits, the normal unsaved-change guard applies.

Returning home does not close, delete, or reset the active project. Project
closing is a distinct explicit command.


## 9. Image-import workspace

The import screen should make a potentially large inspection image set feel
simple to add while keeping validation and provenance visible.

### Page hierarchy

The page header uses **Import images** as the title and a short instruction to
select the complete inspection image set together.

The central import surface provides:
- a prominent **Select images** action;
- **Select folder** where the platform supports it;
- a large but restrained drag-and-drop target where supported.

The drop target uses a neutral dashed/outlined treatment and a simple image/folder
icon. It must not imply that files are already imported merely because they were
dropped or selected.

### Import activity

After selection, the workspace changes from source selection to truthful import
activity. Show a progress indicator only for measurable file validation/copying
work; otherwise use an indeterminate activity indicator plus concrete processed
item counts when available.

The user can distinguish:
**selected -> validating/importing -> persisted/accepted -> needs attention**.

Closing or navigating away during an active import must follow the application
operation guard rather than pretending the import completed.

### Persisted summary

After import, a compact summary band/cards show backend-derived counts such as:
**images · RGB · thermal · pairs · needs attention**.

The summary is visually secondary to the next workflow action. Counts with zero
or unavailable meaning should not become decorative dashboard metrics.

A primary **Start processing** action appears in the page header/action region.
Its enabled/blocked state comes from the workflow service. When blocked, the
reason is visible near the action.

### Attention panel

Unsupported files, parse failures, missing counterparts, and metadata conflicts
appear in a dedicated **Needs attention** region. This is not styled as a single
generic fatal error: items that can coexist with a valid import remain warnings
or review items according to backend rules.

Each row identifies the affected file/evidence and concise reason. Technical
parser details may be expandable for diagnostics without overwhelming the normal
workflow.

Valid unpaired RGB or thermal evidence remains represented distinctly from
invalid/failed files.

### Metadata verification

A compact verification section presents the imported evidence's date/time range
and GPS coverage where trustworthy.

Use range/coverage language for multi-image inspections rather than displaying a
single invented inspection timestamp or coordinate. Missing/conflicting source
metadata is explicitly marked.

If a later implementation supports a manual correction/override, its visual
treatment must clearly distinguish user-entered values from source metadata and
preserve provenance.

### Re-entry and changed source sets

Returning to Import for an unchanged project shows the persisted import summary
rather than an empty drop target as if no work had occurred.

Adding/replacing imagery after downstream processing or review requires a
separate explicit invalidation-aware flow. The normal import screen must not
silently append source data into an already reviewed evidence set.

### Visual relationship to the shell

The import screen uses the light work surface and normal page header. It does not
need the right contextual panel during ordinary selection/import; the center
region should remain calm and wide.

Detailed file/metadata inspection may open a contextual panel without changing
the persisted import state.


## 10. Processing workspace

The processing screen communicates long-running technical work without creating
false precision or requiring users to read logs.

### Overall stage rail

A horizontal stage rail provides orientation across the persisted processing
pipeline. Each stage uses a short label plus explicit state icon/text:
**pending · active · completed · interrupted/failed**.

Completed stages use a quiet confirmation treatment. The active stage receives
the controlled brand accent. Failed/interrupted stages use semantic warning/error
styling without recoloring the entire workspace.

The stage rail reflects backend processing boundaries; it must not invent
presentation-only stages merely to create a smoother-looking progress sequence.

### Active-stage card

The visual center is a large restrained card showing:
- current stage name;
- concise description of current work;
- truthful progress presentation;
- processed/total counters when meaningful;
- elapsed runtime;
- last known activity/heartbeat when supported.

A numeric percentage is displayed only when the backend exposes a meaningful
denominator. Otherwise use an indeterminate activity indicator. A frozen
percentage alone must never be labelled **stuck**.

When counters are available, prefer concrete information such as
**1,572 / 2,316 modules** over decorative animation.

### Overall progress

If the backend can calculate a defensible overall progress measure, it may be
shown separately from active-stage progress and clearly labelled. Do not derive
overall percentage by assigning arbitrary equal weights to unequal processing
stages.

### Details and diagnostics

Normal operation hides technical logs behind **Show details**. The expandable
area may expose stage timings, technical messages, and diagnostic identifiers
useful for support.

Warnings that do not invalidate processing remain visually separate from a
failed stage.

### Interruption and recovery

When persisted state indicates an interrupted/failed recoverable operation, the
normal progress presentation is replaced by a recovery card explaining:
- where processing stopped;
- the last valid persisted boundary;
- what source/derived data remains preserved.

Available actions follow the previously defined semantics:

**Continue** is the visually preferred recovery path when permitted.

**Retry step** is a secondary action and states which failed/interrupted stage
will be rerun.

**Restart processing** is visually separated as a consequential maintenance
action. Selecting it opens a confirmation that states exactly what will be
rebuilt, invalidated, and preserved before execution.

The UI must not offer a recovery action whose invalidation behavior is undefined
for the concrete processing stage.

### Human-review protection

If a requested rebuild would invalidate evidence on which persisted human review
depends, the recovery card must not reduce that situation to a generic
confirmation dialog. The action remains blocked until the explicit
migration/re-review workflow required by the backend/domain contract exists.

### Leaving and returning

Navigating to another permitted area does not imply cancellation. Returning to
Processing reconstructs the screen from persisted operation/workflow state.

Application or operating-system restart follows the same rule: after startup,
SolarCheck rederives processing state and presents the appropriate active,
completed, interrupted, or recovery view.

### Completion transition

When processing completes successfully, the page presents a concise persisted
completion summary and promotes **Open plant overview** as the next primary
action.

No success state is shown solely because a client-side progress animation
reached its end.


## 11. Plant-overview workspace

The plant overview is SolarCheck's primary inspection canvas. It prioritizes
spatial evidence over dashboard decoration and should feel closer to a precise
GIS/inspection workstation than a generic business application.

### Canvas-first layout

After successful processing, the center workspace opens with the complete plant
extent fitted to the available canvas. The RGB inspection mosaic is the default
primary evidence layer when available.

The canvas expands beneath the normal shell:
- dark application header remains compact;
- left workflow navigation remains available;
- center image canvas receives the dominant area;
- right contextual panel stays collapsed until selection/detail requires it.

The viewer background uses a neutral dark/medium surface so missing image extent
is visually distinct from inspection imagery without resembling a thermal value.

### Compact viewer toolbar

A compact floating/docked toolbar provides the frequently used controls:
**RGB · Thermal · Compare**, **Zoom in**, **Zoom out**, **Fit plant**, and layer
visibility.

A reset-overview command may be included if implementation testing shows that it
adds value beyond **Fit plant**.

Controls use icon + accessible label/tooltip. RGB/Thermal/Compare are presented
as mutually exclusive viewing modes rather than unrelated toggle buttons.

### Spatial navigation

Mouse/touchpad interaction follows familiar map/image conventions:
- wheel/gesture zoom centered on the interaction point where practical;
- drag to pan;
- double-click or equivalent may zoom/focus if it does not conflict with module
  selection;
- **Fit plant** restores the complete processed plant extent.

Changing RGB/Thermal/Compare mode, opening details, or changing overlay
visibility preserves center and zoom.

### Layer controls

The viewer exposes a compact layer control for:
- module outlines;
- module IDs where useful at the current zoom;
- finding markers;
- review-state overlay;
- optional background map/satellite orientation layer when available.

Layer state is presentation state only. Hiding an overlay never changes
persisted findings, review, or evidence.

The optional background layer sits beneath the inspection mosaic and is visually
subordinate. If no permitted source is available offline, the control is omitted
or clearly unavailable without producing an error.

### Progressive detail

To prevent large plants becoming visually noisy:
- overview zoom emphasizes plant extent, orientation, and important finding
  markers;
- intermediate zoom introduces module outlines and relevant markers;
- detail zoom may show module identifiers and precise selection geometry.

Thresholds are presentation choices and must not hide the existence of findings;
summary counts/filtering remain available where appropriate.

### Selection

Selecting a module/finding gives it a clear focus outline and opens the right
contextual detail panel. Selection is synchronized with later review/detail
views.

The selected object remains visible when possible as the right panel opens. The
viewer adjusts usable canvas geometry without resetting the user's inspection
context.

Clicking empty canvas may clear selection where this is unambiguous. Closing the
detail panel does not necessarily clear the selected module.

### Finding overview

Finding markers must remain legible over both RGB and thermal imagery. They use
shape/icon plus semantic state rather than color alone.

At broad zoom levels, implementation may cluster or simplify markers for
performance, provided this cannot be mistaken for a reduction in the persisted
finding count. A visible count/filter summary should make the relationship
clear.

### Large-plant performance

The visual contract assumes tiled/pyramidal rendering or another scalable image
strategy for large orthomosaics. The GUI should request/display only the detail
needed for the current viewport and zoom rather than requiring full-resolution
imagery to remain resident.

Temporary tile/detail loading uses subtle placeholders/activity indication and
must not be presented as missing inspection evidence unless the backend actually
reports it missing.

### Next-task affordance

When backend-derived review work exists, a restrained **Start/continue review**
action is available from the plant workspace without obscuring the canvas.

If no review action is currently permitted, the same location explains the
blocker rather than presenting a misleading active button.


## 12. RGB/thermal comparison and module interaction

The comparison experience is designed for direct visual correlation without
turning the viewer into a separate diagnostic authority.

### Compare-mode entry

Selecting **Compare** preserves the current plant viewport and places RGB and
thermal evidence in the same spatial canvas.

On first entry, a slim vertical comparison handle is hinted at the **right edge
of the image workspace**. It is visually separate from the right contextual
panel and includes a concise accessible cue that it can be pulled left.

Dragging the handle from right to left reveals the comparison layer. Once
engaged, the divider can move freely in both directions.

### Wipe presentation

The divider is a thin high-contrast line with a compact grab handle. Labels or
icons identify the RGB and thermal sides so the distinction never depends on
palette recognition.

The wipe is screen-space presentation only. Moving it changes no image
registration, geometry, finding, measurement, or persisted state.

Keyboard operation must allow the divider to be focused and moved in sensible
increments. A reset command returns it to the defined default edge/position.

### View synchronization

Pan and zoom always move RGB, thermal, module geometry, finding overlays, and
the active selection together. Switching among RGB, Thermal, and Compare keeps:
- viewport center;
- zoom;
- selected module/finding;
- relevant overlay visibility.

The last comparison-divider position may be preserved as transient UI state
during the current workspace/session, but it is not inspection evidence.

### Module hover and selection

Where performance allows, hovering a selectable module gives a restrained
preselection outline. Hover must not open a report-style card or obscure
evidence.

Clicking/selecting the module applies a stronger focus treatment and opens the
compact finding/detail box in the right contextual panel.

Selection geometry must remain distinguishable over both RGB and thermal
imagery. The UI may use an outline plus subtle halo/contrast technique rather
than relying on one fixed color.

### Compact finding box

The box follows a stable information order:
1. physical module identity/location where resolved;
2. persisted finding/review state;
3. short coarse finding indication;
4. relevant validated thermal values when available;
5. explicit human-review requirement/state;
6. contextual actions.

Machine-generated classification is labelled as a recommendation and never
styled as an authoritative confirmed diagnosis.

Missing/unvalidated measurements are shown as unavailable, not as zero or an
estimated value.

### Finding actions

Where the backend permits them, **Confirm**, **Unclear**, and **Reject** appear
together with equal semantic clarity. Confirmation is not made visually
tempting merely because it is the first action.

After a review action, the detail box refreshes from persisted state before the
viewer presents the new authoritative status.

A **Report details** / **More in report** action leads to the richer
report-oriented context without duplicating the report model inside the viewer.

### Navigation between relevant modules

The detail region may expose **Previous** / **Next review item** controls when a
review-relevant sequence exists. These controls change selection/focus while
preserving the current comparison mode and useful zoom context.

The sequence is derived from the active review/filter context; it must not imply
that every physical module has a finding.

### No-finding and unclear states

A selected module without a documented finding says so plainly rather than
showing an empty warning-style box.

An unclear finding remains explicitly **Unclear** until authoritative review
changes it. The visual system must not collapse unclear into confirmed,
rejected, or generic warning merely to simplify coloring.

### Evidence-first behavior

The user can hide overlays and contextual panels to inspect unobstructed source
presentation. UI annotations must not be burned into or exported as if they were
part of the source RGB/thermal image.

The comparison viewer provides visual correlation; it does not itself assert
radiometric validation, registration accuracy, or defect diagnosis.


## 13. Review workspace

The review workspace combines a report-like vertical evidence stream with a
synchronized plant viewer. Its purpose is efficient human adjudication while
preserving spatial context and source evidence.

### Split workspace

On typical desktop widths, the review screen uses two coordinated regions:
- a dominant scrollable review stream for evidence cards;
- a persistent plant viewer for spatial orientation and selection.

The split is resizable within sensible limits. Neither side becomes a tiny
decorative preview: the review cards must remain readable and the map must remain
useful for locating modules.

On narrower supported layouts, implementation may switch to a controlled
viewer/stream arrangement, but the synchronized selection model remains the
same.

### Review summary and filters

A compact sticky review header shows persisted counts such as:
**To review · Confirmed · Unclear · Rejected**.

Filters provide **Open**, **Confirmed**, **Unclear**, **Rejected**, and **All**.
The active filter is obvious through text/selection treatment, not color alone.

Counts and filters are derived from persisted review state. Changing a filter
does not change review decisions.

### Review stream

The default stream prioritizes items requiring human attention rather than
rendering every unremarkable physical module.

Cards use the shared light-surface component language and may contain:
- module identity/location;
- current finding/review state;
- RGB evidence crop;
- thermal evidence crop;
- relevant validated thermal values;
- clearly labelled machine recommendation;
- concise reviewer note/status;
- **Confirm · Unclear · Reject** actions;
- **Report details**.

RGB and thermal crops receive comparable visual weight where both exist.
Missing source evidence is represented explicitly; no artificial placeholder
image is styled as if it were inspection evidence.

### Active-card synchronization

As a card becomes actively selected, its physical module is highlighted/focused
in the plant viewer.

Selecting a finding/module in the plant viewer activates and scrolls the
corresponding review card into view.

Automatic synchronization should not constantly steal scroll focus merely
because the map viewport changes. Explicit selection is the authoritative
navigation event.

### Review decision interaction

Decision controls remain in a stable location across cards to support repetitive
professional review without encouraging accidental clicks.

A decision is not visually committed until persistence succeeds. During the
operation, the affected card shows a small bounded busy state. On failure, the
previous persisted status remains and the error is shown next to that card.

After success, counts, filter membership, map overlay, and card state refresh
from persisted data.

If the active filter no longer includes the item after a decision, the
transition to the next relevant card should be predictable and not reset the
plant viewport.

### Focus mode

Difficult cases can enter **Focus mode**. This enlarges RGB/thermal evidence,
measurement/context information, and review controls while retaining:
- current module identity;
- comparison capability where useful;
- **Previous/Next review item** navigation;
- a clear return to the exact stream/filter/map context.

Focus mode is not a separate review model and does not duplicate decisions.

### Notes and detail

Reviewer notes should use a compact expandable field so ordinary cases do not
become visually dominated by text input. Saving notes follows the same persisted
state principle as decisions.

Long report narrative, provenance detail, and report-specific composition stay
behind **Report details** rather than expanding every review card into a full
report page.

### Large-review performance

The stream uses virtualized/lazy card rendering for large inspections. Evidence
thumbnails/crops are loaded as needed and may use neutral loading placeholders.

A loading placeholder must be visually distinct from a genuinely missing RGB or
thermal evidence asset.

### Completion state

When no required review items remain according to backend/domain rules, the
workspace shows a restrained completion state and promotes the next permitted
report action.

This visual completion message does not independently declare a report released
or exportable; report/export readiness is rederived through the application
workflow service.
