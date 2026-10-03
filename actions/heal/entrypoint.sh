#!/bin/bash
set -e

# Configure Git for automated commits
git config --global user.name "yamlr[bot]"
git config --global user.email "bot@yamlr.dev"
git config --global --add safe.directory /github/workspace

echo "Yamlr Manifest Remediator starting..."

# Default to current workspace if not provided
TARGET_PATH=${INPUT_PATH:-"."}
APPLY=${INPUT_APPLY:-false}
PUSH=${INPUT_PUSH:-false}

if [ "$PUSH" = "true" ] && [ "$APPLY" != "true" ]; then
    echo "[ERROR] INPUT_PUSH=true requires INPUT_APPLY=true; pushing is never an implicit apply." >&2
    exit 2
fi

if [ "$PUSH" = "true" ] && [ -n "$(git status --porcelain=v1 --untracked-files=all)" ]; then
    echo "[ERROR] Refusing automatic commit because the workspace had changes before Yamlr started." >&2
    echo "Commit, stash, or restore those changes, then rerun the action." >&2
    exit 1
fi

# Assemble command into an array for safe execution (prevents shell injection)
CMD_ARRAY=("yamlr" "heal" "$TARGET_PATH")

if [ "$APPLY" = "true" ]; then
    CMD_ARRAY+=("--apply")
fi

if [ "${INPUT_DIFF:-false}" = "true" ]; then
    CMD_ARRAY+=("--diff")
fi

if [ "${INPUT_DRY_RUN:-false}" = "true" ]; then
    CMD_ARRAY+=("--dry-run")
fi

K8S_VER="${INPUT_K8S_VERSION:-$INPUT_KUBE_VERSION}"
if [ -n "$K8S_VER" ]; then
    CMD_ARRAY+=("--k8s-version" "$K8S_VER")
fi

if [ -n "$INPUT_CRD" ]; then
    CMD_ARRAY+=("--crd" "$INPUT_CRD")
fi

if [ "${INPUT_HELM:-false}" = "true" ]; then
    CMD_ARRAY+=("--helm")
fi

if [ "${INPUT_KUSTOMIZE:-false}" = "true" ]; then
    CMD_ARRAY+=("--kustomize")
fi

if [ -n "$INPUT_INGEST_OPA" ]; then
    CMD_ARRAY+=("--ingest-opa" "$INPUT_INGEST_OPA")
fi

if [ -n "$INPUT_INGEST_KYVERNO" ]; then
    CMD_ARRAY+=("--ingest-kyverno" "$INPUT_INGEST_KYVERNO")
fi

if [ -n "$INPUT_OUTPUT_FILE" ]; then
    CMD_ARRAY+=("--output-file" "$INPUT_OUTPUT_FILE")
fi

if [ "${INPUT_EXIT_ZERO:-false}" = "true" ]; then
    CMD_ARRAY+=("--exit-zero")
fi

if [ "${INPUT_PUSH_TELEMETRY:-false}" = "true" ]; then
    CMD_ARRAY+=("--push-telemetry")
fi

# Parse extra args reliably
if [ -n "${INPUT_EXTRA_ARGS:-}" ]; then
    read -ra EXTRA_ARGS <<< "$INPUT_EXTRA_ARGS"
    CMD_ARRAY+=("${EXTRA_ARGS[@]}")
fi

echo "Running: ${CMD_ARRAY[*]}"

# Execute via direct array call (no eval)
"${CMD_ARRAY[@]}"

# Commit and push only when explicitly requested. The preflight requires a clean
# starting tree so pre-existing user changes cannot enter the commit.
if [ "$PUSH" = "true" ]; then
  bash /stage_manifest_changes.sh "$TARGET_PATH"
  if ! git diff --cached --quiet; then
    echo "Remediations applied. Committing changed manifests..."
    git commit -m "chore(yamlr): automated Kubernetes manifest remediation"
    echo "Pushing remediations back to branch..."
    git push
  else
    echo "No changed YAML manifests found under '$TARGET_PATH'."
  fi
else
  if [ "$APPLY" = "true" ]; then
    echo "Applied changes remain in the workspace; set INPUT_PUSH=true to commit and push them."
  else
    echo "Preview complete; no files were changed."
  fi
fi
