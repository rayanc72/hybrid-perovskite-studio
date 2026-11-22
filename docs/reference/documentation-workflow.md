# Documentation workflow

## Organize for the reader

- `docs/user-guide/`: installation, navigation, examples, troubleshooting.
- `docs/tutorials/`: complete scientific workflows with inputs and expected results.
- `docs/features/`: task controls, outputs, and workspace-specific limitations.
- `docs/reference/`: input formats, scientific conventions, validation, and maintenance references.
- `docs/developer/`: development setup, architecture links, and implementation pointers.
- `docs/changelog.md`: user-visible changes.

Keep implementation details in the developer guide. Explain scientific assumptions,
units, data handling, and interpretation in the user-facing guide where they affect decisions.

## Update with a feature

1. Match exact UI workspace/view/group/tool labels and available export formats.
2. Update the corresponding workspace guide and complete tutorial.
3. Update `src/hps/examples/projects/*.json` guide routes and actions. Summary steps
   omit `view`; tool steps use separate `view`, `group`, and `tool` fields.
4. Review expected result names against current scientific terminology. Distinguish
   finite molecules from periodic networks and original data from sampled fixtures.
5. Update the changelog, version baseline, and verification date. Link version-specific
   application source pointers to its tag; use `main` for current maintenance procedures.
6. Update navigation or architecture references when their ownership or boundaries change.

## Verify before publishing

```bash
python scripts/build_doc_examples.py
python -m pytest tests/test_examples.py -q
python -m mkdocs build --strict
```

Example tests validate manifest routes against the navigation registry and exercise
bundle contents, including the ready-to-upload trajectory archive. MkDocs checks
local links and builds the site. These checks do not establish that external services
are available; the scheduled documentation-link workflow checks external Markdown
links weekly and can also be run manually. Authentication, rate limits, and bot
blocking may require manual investigation of a reported external failure.

After deployment, open the home page, one complete tutorial, and all example download
links. Confirm the visible version baseline matches the application instructions.
Use the [feature template](https://github.com/rayanc72/hybrid-perovskite-studio/blob/main/docs/templates/feature-template.md) for new workflows.

## Review checklist

- [ ] A new user can obtain the inputs and reproduce a complete result.
- [ ] Navigation, filenames, units, scientific assumptions, and exports match the app.
- [ ] Packaged examples and documentation downloads match the described bundle versions.
- [ ] Version labels and source links distinguish `main`, release tags, and PyPI.
- [ ] Screenshots support the text and contain no private information.
- [ ] Relevant tests and the strict build pass; published links and downloads work.
