# Hybrid Perovskite Studio Docs

This documentation set is organized around the current workspace-based UI. The goal is to help someone understand the app quickly, then drill into the relevant workspace and tool family.

## Start Here

- [Getting Started](user-guide/getting-started.md)
- [Screenshots](user-guide/screenshots.md)
- [Feature Map](feature-map.md)
- [Navigation and Workspaces](user-guide/navigation-and-workspaces.md)
- [Architecture](architecture.md)
- [Backend Modernization](reference/backend-modernization.md)
- [Documentation Workflow](reference/documentation-workflow.md)
- [Development TODO](../TODO.md)
- [Changelog](changelog.md)

## Workspace Guides

- [Structure Workspace](features/structure-workspace.md)
- [Electronic Workspace](features/electronic-workspace.md)
- [Band Structure Studio](features/band-structure-studio.md)
- [Dynamics Workspace](features/dynamics-workspace.md)
- [Utilities Workspace](features/utilities-workspace.md)

## What The Docs Cover

The docs focus on:

- how the current UI is organized
- what each workspace does
- the major tools available in each workspace
- what inputs and outputs each workspace expects
- where the active code lives
- which workflows already use the local backend job/cache layer

## Source Of Truth For Navigation

The current workspace map and feature tree are defined in:

- [src/hps/ui/navigation.py](../src/hps/ui/navigation.py)

If the visible navigation changes, that file and the matching workspace doc should be updated together.
