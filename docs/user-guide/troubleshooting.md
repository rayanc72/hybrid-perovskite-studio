# Troubleshooting

## Backend not ready on first launch

The app waits up to five seconds for the local backend. On a cold start, imports can
take longer and show a readiness warning even though the process is still starting.
Wait a little, refresh, and retry. A warning that persists needs investigation.

Inspect the terminal and the backend log. Print the configured log location without
assuming a particular installation directory:

```bash
python -c "from hps.io.paths import APP_BACKEND_LOG; print(APP_BACKEND_LOG)"
```

You can start the backend manually in another terminal with the same environment:

```bash
hps-backend --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765/health`; a healthy response identifies `hps-backend`,
reports `status: ok`, and includes its version. If an earlier backend process is
already healthy, reuse it rather than starting another one on the same port.

## Port already in use

The backend defaults to port 8765. Choose an unused port before launching HPS:

```bash
# macOS/Linux
export HPS_BACKEND_PORT=8766
hps
```

```powershell
# Windows PowerShell
$env:HPS_BACKEND_PORT = "8766"
hps
```

Remove an old `HPS_BACKEND_URL` override if it points elsewhere. That variable takes
precedence when resolving the service URL; use it only for an intentionally managed
compatible backend. Keep the normal local host `127.0.0.1`.

For the Streamlit interface port, set `STREAMLIT_SERVER_PORT` before running `hps`.
The `hps` launcher does not forward arbitrary Streamlit command-line flags.

## Missing modules, installation failures, or hps not found

- Activate the environment used for installation, then check `python -m pip show hybrid-perovskite-studio`.
- Install the `[full]` extra using the tagged command in [Getting started](getting-started.md).
- Check the Python version and the first dependency error. Optional DiffPy PDF support
  requires the separate `[pdf]` extra and platform-compatible binaries.
- If activation is unavailable, use the virtual environment's Python and launcher directly.
- If controls differ from these guides, check whether you installed PyPI v0.2.1 instead of GitHub v0.3.0.

## Upload rejected or data missing

Check the workflow-specific [input requirements](../reference/input-formats.md).
For trajectories, upload only one frame archive, use `geometry*.in` for interactive
analyses, and keep atom counts and ordering consistent. Archive extraction rejects
unsafe paths, links, excessive entry counts, and oversized contents; the browser's
upload limit can be lower than the extraction limit.

For bands, keep the original filenames and upload all segments for one calculation
into one dataset. Missing `geometry.in` prevents Brillouin-zone generation but not
band plotting. Missing `control.in` changes path-label behavior.

## Excel export unavailable or selection rejected

Upload recognized band files, select at least one dataset and segment, and choose
state offsets that exist in each selected dataset. `0` means the detected VBM state;
`-1,0,1` and `-2:3` are valid offset syntax. This differs from the plot segment filter,
which uses one-based segment indices and hyphenated ranges such as `1,3-4`.

## A molecule is missing from a rotation selector

Only finite bonded groups are offered for finite-molecule operations. Periodic
networks retain their original group numbers and are available for other operations
such as labelling, translation, and deletion. Inspect **Molecule groups and names**
and the [bonding model](../reference/input-formats.md#structures-and-bonded-groups)
before adjusting detection settings.

## JupyterLite cannot see uploaded files

The Utilities notebook runs in a separate browser environment. Import files into that
environment explicitly; uploads to another HPS workspace are not shared with it.

## Report a reproducible problem

Open a [GitHub issue](https://github.com/rayanc72/hybrid-perovskite-studio/issues) with
the HPS version, Python version, operating system, workspace/tool, exact steps, and a
small redistributable example. Review logs and screenshots before attaching them;
remove private filesystem paths, credentials, and unpublished research data.
