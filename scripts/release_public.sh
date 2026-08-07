#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/release_public.sh --commits <sha1,sha2,...> [options]

Curate a public release by cherry-picking selected private commits onto a
temporary branch created from the public branch.

Required:
  --commits <list>       Comma-separated commit SHAs to cherry-pick, in order.

Options:
  --release-branch <n>   Release branch name to create.
  --public-remote <n>    Public remote name. Default: public
  --private-branch <n>   Private branch name. Default: main
  --public-branch <n>    Local public tracking branch. Default: public-main
  --push                 Push the release branch to the public remote.
  --tag <name>           Create an annotated tag on the release branch tip.
  --yes                  Skip the confirmation prompt.
  -h, --help             Show this help text.

Example:
  scripts/release_public.sh \
    --commits f21b793,abc1234 \
    --release-branch release/public-v0.4.0 \
    --tag v0.4.0 \
    --push
EOF
}

require_clean_worktree() {
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "Working tree is not clean. Commit or stash changes before releasing." >&2
    exit 1
  fi
}

ensure_branch_exists() {
  local branch="$1"
  if ! git show-ref --verify --quiet "refs/heads/${branch}"; then
    echo "Local branch '${branch}' does not exist." >&2
    exit 1
  fi
}

ensure_remote_exists() {
  local remote="$1"
  if ! git remote get-url "${remote}" >/dev/null 2>&1; then
    echo "Remote '${remote}' does not exist." >&2
    exit 1
  fi
}

ensure_commit_on_branch() {
  local commit="$1"
  local branch="$2"
  if ! git merge-base --is-ancestor "${commit}" "${branch}"; then
    echo "Commit '${commit}' is not reachable from '${branch}'." >&2
    exit 1
  fi
}

confirm_or_exit() {
  local release_branch="$1"
  local public_remote="$2"
  local tag_name="$3"
  shift 3
  local commits=("$@")

  echo "About to create '${release_branch}' from '${PUBLIC_BRANCH}' and cherry-pick:"
  for commit in "${commits[@]}"; do
    echo "  - ${commit} $(git log -1 --format=%s "${commit}")"
  done
  echo "Public remote: ${public_remote}"
  if [[ -n "${tag_name}" ]]; then
    echo "Tag to create: ${tag_name}"
  fi

  if [[ "${ASSUME_YES}" == "true" ]]; then
    return
  fi

  read -r -p "Continue? [y/N] " reply
  if [[ ! "${reply}" =~ ^[Yy]$ ]]; then
    echo "Release cancelled."
    exit 0
  fi
}

COMMITS_RAW=""
RELEASE_BRANCH=""
PUBLIC_REMOTE="public"
PRIVATE_BRANCH="main"
PUBLIC_BRANCH="public-main"
PUSH_RELEASE="false"
ASSUME_YES="false"
TAG_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --commits)
      COMMITS_RAW="${2:-}"
      shift 2
      ;;
    --release-branch)
      RELEASE_BRANCH="${2:-}"
      shift 2
      ;;
    --public-remote)
      PUBLIC_REMOTE="${2:-}"
      shift 2
      ;;
    --private-branch)
      PRIVATE_BRANCH="${2:-}"
      shift 2
      ;;
    --public-branch)
      PUBLIC_BRANCH="${2:-}"
      shift 2
      ;;
    --push)
      PUSH_RELEASE="true"
      shift
      ;;
    --tag)
      TAG_NAME="${2:-}"
      shift 2
      ;;
    --yes)
      ASSUME_YES="true"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "${COMMITS_RAW}" ]]; then
  echo "--commits is required." >&2
  usage >&2
  exit 1
fi

IFS=',' read -r -a COMMITS <<< "${COMMITS_RAW}"
if [[ ${#COMMITS[@]} -eq 0 ]]; then
  echo "Provide at least one commit SHA." >&2
  exit 1
fi

if [[ -z "${RELEASE_BRANCH}" ]]; then
  RELEASE_BRANCH="release/public-$(date +%Y%m%d-%H%M%S)"
fi

require_clean_worktree
scripts/check_release.sh
ensure_remote_exists "${PUBLIC_REMOTE}"
ensure_branch_exists "${PRIVATE_BRANCH}"
ensure_branch_exists "${PUBLIC_BRANCH}"

current_branch="$(git branch --show-current)"
if [[ "${current_branch}" != "${PRIVATE_BRANCH}" ]]; then
  echo "Run this script from '${PRIVATE_BRANCH}'. Current branch: '${current_branch}'." >&2
  exit 1
fi

for commit in "${COMMITS[@]}"; do
  if ! git rev-parse --verify "${commit}^{commit}" >/dev/null 2>&1; then
    echo "Commit '${commit}' does not exist." >&2
    exit 1
  fi
  ensure_commit_on_branch "${commit}" "${PRIVATE_BRANCH}"
done

if git show-ref --verify --quiet "refs/heads/${RELEASE_BRANCH}"; then
  echo "Local release branch '${RELEASE_BRANCH}' already exists." >&2
  exit 1
fi

if git ls-remote --exit-code --heads "${PUBLIC_REMOTE}" "${RELEASE_BRANCH}" >/dev/null 2>&1; then
  echo "Remote release branch '${RELEASE_BRANCH}' already exists on '${PUBLIC_REMOTE}'." >&2
  exit 1
fi

confirm_or_exit "${RELEASE_BRANCH}" "${PUBLIC_REMOTE}" "${TAG_NAME}" "${COMMITS[@]}"

git fetch "${PUBLIC_REMOTE}"
git switch "${PUBLIC_BRANCH}"
git pull --ff-only "${PUBLIC_REMOTE}" "$(git rev-parse --abbrev-ref "${PUBLIC_BRANCH}@{upstream}" | cut -d/ -f2)"
git switch -c "${RELEASE_BRANCH}"

for commit in "${COMMITS[@]}"; do
  echo "Cherry-picking ${commit}..."
  git cherry-pick -x "${commit}"
done

if [[ -n "${TAG_NAME}" ]]; then
  git tag -a "${TAG_NAME}" -m "Public release ${TAG_NAME}"
fi

if [[ "${PUSH_RELEASE}" == "true" ]]; then
  git push -u "${PUBLIC_REMOTE}" "${RELEASE_BRANCH}"
  if [[ -n "${TAG_NAME}" ]]; then
    git push "${PUBLIC_REMOTE}" "${TAG_NAME}"
  fi
fi

echo
echo "Release branch ready: ${RELEASE_BRANCH}"
echo "Base branch: ${PUBLIC_BRANCH}"
if [[ "${PUSH_RELEASE}" == "true" ]]; then
  echo "Pushed to remote: ${PUBLIC_REMOTE}"
else
  echo "Not pushed yet. Review locally, then push with:"
  echo "  git push -u ${PUBLIC_REMOTE} ${RELEASE_BRANCH}"
fi
if [[ -n "${TAG_NAME}" ]]; then
  echo "Tag created: ${TAG_NAME}"
fi
