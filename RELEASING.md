# Releasing To The Public Repo

This repository now has two Git remotes:

- `origin`: the private internal repository
- `public`: the public release repository

The local branches are set up to match that split:

- `main`: internal development branch tracked against `origin/main`
- `public-main`: local tracking branch for `public/main`

## Recommended workflow

1. Do day-to-day development in the private repo on `main` and short-lived feature branches.
2. Keep commits small and self-contained so public releases can cherry-pick only the work that is ready.
3. Keep internal release notes in `docs/changelog.md`, especially under `## Unreleased`.
4. When a set of commits is ready for public release, run `scripts/release_public.sh` from `main`.
5. Review and test the generated release branch before pushing or merging it to the public repo.

## Choosing commits for a public release

List the candidate commits from private `main`:

```bash
git log --oneline public-main..main
```

That range shows commits that exist privately but are not yet on the public branch. Pick only the commits that are ready to ship.

## Scripted release flow

Create a public release branch and cherry-pick the approved commits:

```bash
scripts/release_public.sh \
  --commits <sha1,sha2,...> \
  --release-branch release/public-v0.4.0
```

Push the release branch to the public remote after local review:

```bash
git push -u public release/public-v0.4.0
```

Or let the script push and tag for you:

```bash
scripts/release_public.sh \
  --commits <sha1,sha2,...> \
  --release-branch release/public-v0.4.0 \
  --tag v0.4.0 \
  --push
```

## What the script checks

- the modern package layers pass Ruff correctness checks
- the full test suite passes with a headless plotting backend
- the documentation builds in strict mode
- source and wheel distributions build successfully
- the working tree is clean
- you are running from `main`
- `public` exists
- `main` and `public-main` exist locally
- each selected commit exists and is reachable from private `main`
- the release branch does not already exist locally or on the public remote

## After the script runs

1. Review the release branch diff against `public-main`.
2. Run the tests and any manual checks you want for the public release.
3. Update `docs/changelog.md` if you want the public release branch to carry a dated release section.
4. Push the release branch to `public`.
5. Open a PR against the public repository or merge directly if that is your preferred release process.

## Useful commands

Show private-only commits:

```bash
git log --oneline public-main..main
```

Inspect what the release branch changed:

```bash
git diff public-main...HEAD
```

See which remote each branch tracks:

```bash
git branch -vv
```

## Notes

- The script uses `git cherry-pick -x` so the public commit message keeps a reference to the original private commit.
- If a cherry-pick conflicts, Git will stop and let you resolve it manually. After that, continue with `git cherry-pick --continue`.
- If you decide to abandon the release branch, switch away from it and delete it with `git branch -D <release-branch>`.
