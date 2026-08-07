# Navigation And Workspaces

## Overview

The current UI is built around a landing page plus four workspaces:

- Structure
- Electronic
- Dynamics
- Utilities

Users start on a minimal landing page, then open a workspace from the top card row.

## Workspace Gallery

### Landing page

![Hybrid Perovskite Studio landing page](../images/screenshots/landing-page.png)

### Structure workspace

![Structure workspace](../images/screenshots/structure-workspace.png)

### Band Structure Studio

![Band Structure Studio](../images/screenshots/band-structure-studio.png)

### Dynamics workspace

![Dynamics workspace](../images/screenshots/dynamics-workspace.png)

## Landing Page

The landing page shows:

- centered app branding
- a short introduction
- one card for each workspace
- an optional `Browse feature map` expander

The feature map is generated from the same navigation registry that powers the visible workspace selectors.

## Workspace Selection

Each workspace card includes an `Open ...` button. Clicking it:

- activates that workspace
- updates the active card state
- switches the main page to the corresponding workspace

Users can return to the start page with the `Start Page` button.

## Feature Map

The `Browse feature map` expander shows a tree of the app’s current capabilities.

This tree is generated from:

- [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py)

That file is the current single source of truth for:

- workspace names
- workspace descriptions
- workspace views
- grouped tools
- feature-map structure

## Structure Workspace Pattern

The Structure workspace is more layered than the others:

- `Overview`
- `Analysis`
- `Transformations`

`Analysis` and `Transformations` each introduce a second selection level such as `Group` and then `Tool`.

The current `Structure -> Analysis` groups include:

- `Symmetry`
- `Molecules`
- `Structure Metrics`
- `PXRD Analysis`
- `PDF Analysis`

## Other Workspaces

- Electronic uses `View` plus `Tool`.
- Dynamics uses `View` to switch between direct MD output and trajectory analysis.
- Utilities uses `View` to select between script execution and generic plotting/data utilities.

## Why This Matters For Docs

When the app navigation changes, the documentation should be updated in two places:

- the relevant workspace guide in `docs/features/`
- [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py) if the visible feature tree changed
