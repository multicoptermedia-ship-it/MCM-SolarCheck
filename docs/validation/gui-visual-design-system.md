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
