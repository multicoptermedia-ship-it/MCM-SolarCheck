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
