# Getting started

## Choose the matching version

| Source | Application version | Use these guides for |
| --- | --- | --- |
| GitHub tag `v0.3.0` | 0.3.0 | Current application workflows, including CIF and Excel exports and no-SOC bands |
| Public GitHub `main` | 0.3.0 plus subsequent source changes | Current documentation and improved example packaging |
| PyPI | 0.2.1 | Older application; some controls in these guides are unavailable |

For the application described here, install the **GitHub tag**. Documentation changes
do not move existing release tags or replace published packages.

## Prerequisites

- Python **3.11 or newer**; Python 3.11 is the release-check baseline.
- Git for the GitHub installation command.
- A writable Python virtual environment and a browser.

Check `python3.11 --version` and `git --version` on macOS/Linux, or
`py -3.11 --version` and `git --version` on Windows. A newer compatible Python can
replace 3.11, although optional scientific binaries may have narrower support.

## Install and run

### macOS and Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install "hybrid-perovskite-studio[full] @ git+https://github.com/rayanc72/hybrid-perovskite-studio.git@v0.3.0"
hps
```

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install "hybrid-perovskite-studio[full] @ git+https://github.com/rayanc72/hybrid-perovskite-studio.git@v0.3.0"
hps
```

If PowerShell blocks activation, use Command Prompt with
`.venv\Scripts\activate.bat`, or run `.venv\Scripts\python.exe -m pip` and
`.venv\Scripts\hps.exe` directly. Activation is a convenience, not a requirement.

Open the local URL printed in the terminal, usually `http://localhost:8501`.
Keep the terminal running; stop the application with **Ctrl+C**. On subsequent runs,
activate the same environment and run `hps`.

Verify the installed version in a second terminal using that environment:

```bash
python -c "import hps; print(hps.__version__)"
python -m pip show hybrid-perovskite-studio
```

The tagged installation should report `0.3.0`. If the first launch briefly reports
that the backend is not ready, allow startup to finish and refresh. See
[Troubleshooting](troubleshooting.md#backend-not-ready-on-first-launch) if it persists.

## Optional pair distribution function dependencies

The `[full]` extra supplies the application stack but **does not include DiffPy PDF
simulation dependencies**. To add them to the same tagged installation:

```bash
python -m pip install "hybrid-perovskite-studio[full,pdf] @ git+https://github.com/rayanc72/hybrid-perovskite-studio.git@v0.3.0"
```

`diffpy.pdffit2` and `diffpy.structure` availability depends on the operating system,
Python version, and binary build requirements. Other workspaces can be used without
these dependencies. See [Known limitations](../reference/known-limitations.md).

## If you need the older PyPI release

In a separate virtual environment, install:

```bash
python -m pip install "hybrid-perovskite-studio[full]==0.2.1"
hps
```

Installing only the base package provides the launcher and dependency guidance;
`[full]` adds the application dependencies. This does not upgrade PyPI to v0.3.0.

## First-time workflow

1. Download and extract the [Structure example](../downloads/hps-example-structure.zip).
2. Open **Structure** from the start page.
3. Upload `data/structure/MC3I_PbI_100K.in` using the upload box at the top.
4. Inspect **Current Structure**: 156 atoms and formula `C32H88I24N8Pb4`.
5. Follow the [structure tutorial](../tutorials/structure.md), or choose another
   [guided example](guided-examples.md).

The four workspaces are **Structure**, **Electronic**, **Dynamics**, and **Utilities**.
Return using **Start Page**; **Explore every tool** opens the feature map.

## Local runtime and data

The standard launch uses a local Streamlit server and a backend at
`http://127.0.0.1:8765`. Scientific processing runs on the machine hosting HPS;
backend jobs may retain inputs or derived artifacts in its runtime directories.
Browser-hosted JupyterLite has a separate filesystem and does not see files uploaded
elsewhere in HPS. Online documentation, browser tools, and package installation
require their respective network access. See [runtime limitations](../reference/known-limitations.md#runtime-model).

For source development, use the [developer setup](../developer/index.md).
