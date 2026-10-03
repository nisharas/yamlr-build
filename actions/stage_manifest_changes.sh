#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 || -z "$1" ]]; then
    echo "Usage: stage_manifest_changes.sh <target-path>" >&2
    exit 2
fi

TARGET_PATH="$1"
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
    echo "[ERROR] Autocommit requires a Git working tree." >&2
    exit 2
fi

stage_manifest_paths() {
    local path
    while IFS= read -r -d '' path; do
        case "$path" in
            *.yaml|*.yml) git add -- "$path" ;;
        esac
    done
}

git diff --name-only --diff-filter=ACMT -z -- "$TARGET_PATH" | stage_manifest_paths
git ls-files --others --exclude-standard -z -- "$TARGET_PATH" | stage_manifest_paths

if git diff --cached --quiet; then
    echo "No changed YAML manifests found under '$TARGET_PATH'."
else
    echo "Staged changed YAML manifests under '$TARGET_PATH'."
fi
