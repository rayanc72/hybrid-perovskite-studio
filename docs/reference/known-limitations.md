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
- Uploaded scientific data stays local unless the user explicitly exports or shares it.
  Job metadata excludes base64-encoded upload contents.

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
  dependency groups. Install `hybrid-perovskite-studio[full]` for the supported complete
  application stack.

## Modernization status

The backend-facing core, service, API, examples, and Structure workspace layers are
covered by the strengthened release lint gate. Older Electronic, Dynamics, Utilities,
and domain visualization modules remain functional and tested, but retain formatting
and session-state debt. Follow-up work is tracked in the repository `TODO.md` and is not
silently treated as completed release work.
