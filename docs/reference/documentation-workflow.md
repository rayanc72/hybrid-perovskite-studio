# Documentation Workflow

## Goal

Keep documentation changes scoped to the exact functionality that changed so feature updates stay easy to review and maintain.

## File organization

- `docs/index.md`: top-level docs navigation
- `docs/user-guide/`: onboarding and cross-feature usage guidance
- `docs/features/`: one file per major feature area
- `docs/reference/`: process docs, conventions, and technical references
- `docs/changelog.md`: user-visible changes

## Update rules

When a feature changes:

1. Update the matching file in `docs/features/`.
2. Update `docs/changelog.md` if behavior, UI labels, dependencies, or outputs changed.
3. Update `docs/index.md` if a new feature doc is added or removed.
4. Update `docs/architecture.md` only if package structure, module ownership, or runtime boundaries changed.

## Recommended feature-doc style

Each feature file should include:

- What it does
- Where it appears in the UI
- Inputs
- Outputs
- How to use it
- Known limitations
- Code touchpoints
- Last verified against code

## Verification workflow

Before merging a feature change:

- Confirm the described sidebar labels still match the app.
- Confirm the described outputs still exist.
- Confirm the listed code touchpoints still point to the active implementation.
- Add a short entry to `docs/changelog.md` if users will notice the change.

## Suggested PR checklist

- [ ] Feature documentation updated
- [ ] Changelog updated if user-visible behavior changed
- [ ] Architecture doc updated if module boundaries changed
- [ ] New files follow the feature template
