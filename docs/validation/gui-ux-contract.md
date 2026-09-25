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
