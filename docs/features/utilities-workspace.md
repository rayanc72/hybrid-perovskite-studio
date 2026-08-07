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
- downloadable exports where supported

## Notes And Limitations

- Utility workflows are broader and less constrained than the domain-specific workspaces.
- Utility workflows are implemented in a focused workspace module and coordinated by the main app.

## Code Touchpoints

- Workspace UI:
  [src/hps/ui/workspaces/utilities.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/workspaces/utilities.py)
- Navigation registry:
  [src/hps/ui/navigation.py](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/src/hps/ui/navigation.py)

## Last Verified

- Date: 2026-08-07
