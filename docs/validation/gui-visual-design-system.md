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
