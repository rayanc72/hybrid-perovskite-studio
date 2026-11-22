# Known limitations

Hybrid Perovskite Studio is research software. The release gate verifies maintained
workflows against published scientific examples, but it does not imply that every
combination of material, simulation code, or optional dependency has been validated.

## Runtime model

- HPS is a local desktop-style Streamlit application. Its backend binds to
  `127.0.0.1` and does not provide authentication for network deployment.
- Backend jobs run in the local Python process. They improve rerun behavior and artifact
  reuse, but are not a distributed queue and do not survive deletion of the local HPS
  runtime directory.
- Scientific processing uses the machine hosting HPS. Backend jobs may retain inputs
  and derived artifacts in local runtime storage. Job metadata excludes base64-encoded
  upload contents. Browser-hosted tools and online resources have separate network
  and filesystem behavior; JupyterLite cannot access other workspace uploads.
- A cold backend start can exceed the five-second readiness window. Wait and refresh;
  see [Troubleshooting](../user-guide/troubleshooting.md#backend-not-ready-on-first-launch)
  if the warning persists.

## Scientific scope

- The electronic-structure importers are primarily validated against FHI-aims-style
  files. Other formats may need conversion.
- Scientific regression coverage uses the maintained examples described in
  [Scientific fixture validation](scientific-validation.md); results outside that scope
  should be independently checked before publication.
- The bundled molecular-dynamics example is a centered 50 fs slice sampled every
  0.5 fs. It is intended to validate parsing and analysis, not long-time statistics.

## Optional features

- PDF workflows based on `diffpy` are an optional installation because compatible
  binary dependencies vary by platform.
- Some visualization and authentication features require the `viz` or `auth` optional
  dependency groups. The `[full]` extra supplies those groups but excludes DiffPy PDF
  dependencies; use the version-specific [installation guide](../user-guide/getting-started.md).

## Input conventions

The backend trajectory inventory accepts more formats than the interactive
MDAnalysis path, which expects `geometry*.in`. See [input formats](input-formats.md)
for filenames, timing, units, and archive limits. The current MDAnalysis builder
loads frames after the first into its trajectory, so interactive analyses can have
one fewer frame than the backend summary. Verify the effective frame count and
time origin before interpreting time-dependent results.
