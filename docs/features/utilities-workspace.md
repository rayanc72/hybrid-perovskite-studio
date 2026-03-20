# Utilities Workspace

## Overview

The Utilities workspace contains general-purpose tools that do not fit naturally into the Structure, Electronic, or Dynamics workspaces.

## Where It Appears In The UI

- Start page workspace card: `Utilities`
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
- Some helpers still live directly in [src/hpame/ui/app_main.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/app_main.py).

## Code Touchpoints

- UI:
  [src/hpame/ui/app_main.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/app_main.py)
- Navigation registry:
  [src/hpame/ui/navigation.py](/Users/rayanchakraborty/hPAME/src/hpame/ui/navigation.py)

## Last Verified

- Date: 2026-03-19
