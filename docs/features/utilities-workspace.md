# Utilities Workspace

## Overview

The Utilities workspace contains general-purpose tools that do not fit naturally into the Structure, Electronic, or Dynamics workspaces.

## Where It Appears In The UI

- Landing-page workspace: `Utilities`
- Workspace views:
  - `Run your own script`
  - `Plot Data`

## Run Your Own Script

This tool opens a JupyterLite-powered browser workspace for running Python directly in the app context.

Current note from the app:

- this environment runs in the browser
- it does not currently have access to files uploaded elsewhere in the app session

## Plot Data

This tool provides general data plotting and dataset modification support for uploaded data files.

Capabilities in the current implementation include:

- upload generic data files
- configure plot settings
- transform datasets with math expressions
- generate custom visualizations

See [table parsing and expression examples](../reference/input-formats.md#general-tables-and-math-expressions)
for safe column names, supported functions, and units.

## Typical Workflow

1. Open the `Utilities` workspace.
2. Choose the target utility.
3. Upload data if needed.
4. Configure the script or plotting options.
5. Inspect the results and export if available.

## Inputs

- optional uploaded data files
- plotting configuration
- math expressions for dataset transformation

## Outputs

- transformed datasets
- plots
- PNG and PDF plot downloads
- reusable plot configuration JSON

## Notes And Limitations

- Utility workflows are broader and less constrained than the domain-specific workspaces.

## Last Verified

- Application baseline: [GitHub v0.3.0](https://github.com/rayanc72/hybrid-perovskite-studio/releases/tag/v0.3.0)
- Documentation reviewed: 2026-11-22
