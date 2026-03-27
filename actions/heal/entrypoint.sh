#!/bin/bash
set -e

# Configure Git for the Surgeon
git config --global user.name "yamlr-surgeon[bot]"
git config --global user.email "surgeon@yamlr.dev"
git config --global --add safe.directory /github/workspace

echo "🔪 Yamlr Surgeon starting..."

# Default to current workspace if not provided
TARGET_PATH=${INPUT_PATH:-"."}

# [Security] Path Sanitization: Ensure inputs don't escape workspace
if [ -n "$INPUT_ADAPTERS_DIR" ]; then
    REAL_BASE=$(realpath -m "$GITHUB_WORKSPACE")
    REAL_INPUT=$(realpath -m "$INPUT_ADAPTERS_DIR")
    if [[ "$REAL_INPUT" != "$REAL_BASE"* ]]; then
        echo "❌ ERROR: adapters-dir must be within current workspace ($GITHUB_WORKSPACE)"
        exit 1
    fi
fi

# Run the native Pro healer
# Assemble command into an array for safe execution (prevents shell injection)
CMD_ARRAY=("yamlr" "heal" "$TARGET_PATH" "--confirm")

# Parse extra args reliably
if [ -n "${INPUT_EXTRA_ARGS:-}" ]; then
    read -ra EXTRA_ARGS <<< "$INPUT_EXTRA_ARGS"
    CMD_ARRAY+=("${EXTRA_ARGS[@]}")
fi

if [ "${INPUT_HARDEN:-false}" = "true" ]; then CMD_ARRAY+=("--harden"); fi
if [ "${INPUT_ENFORCE_LIMITS:-false}" = "true" ]; then CMD_ARRAY+=("--enforce-limits"); fi
if [ "${INPUT_ENFORCE_PROBES:-false}" = "true" ]; then CMD_ARRAY+=("--enforce-probes"); fi
if [ "${INPUT_FIX_REFS:-false}" = "true" ]; then CMD_ARRAY+=("--fix-refs"); fi
if [ "${INPUT_FIX_TAGS:-false}" = "true" ]; then CMD_ARRAY+=("--fix-tags"); fi
if [ -n "$INPUT_KUBE_VERSION" ]; then CMD_ARRAY+=("--kube-version" "$INPUT_KUBE_VERSION"); fi
if [ -n "$INPUT_MAX_DEPTH" ]; then CMD_ARRAY+=("--max-depth" "$INPUT_MAX_DEPTH"); fi
if [ -n "$INPUT_EXT" ]; then CMD_ARRAY+=("--ext" "$INPUT_EXT"); fi
if [ -n "$INPUT_CONCURRENCY" ]; then CMD_ARRAY+=("--concurrency" "$INPUT_CONCURRENCY"); fi
if [ -n "$INPUT_IDENTITY_MODE" ]; then CMD_ARRAY+=("--identity-mode" "$INPUT_IDENTITY_MODE"); fi
if [ "${INPUT_STRICT:-false}" = "true" ]; then CMD_ARRAY+=("--strict"); fi
if [ "${INPUT_COMPACT:-false}" = "true" ]; then CMD_ARRAY+=("--compact"); fi
if [ -n "$INPUT_CPU_LIMIT" ]; then CMD_ARRAY+=("--cpu-limit" "$INPUT_CPU_LIMIT"); fi
if [ -n "$INPUT_MEM_LIMIT" ]; then CMD_ARRAY+=("--mem-limit" "$INPUT_MEM_LIMIT"); fi
if [ -n "$INPUT_NAMESPACE" ]; then CMD_ARRAY+=("--namespace" "$INPUT_NAMESPACE"); fi
if [ -n "$INPUT_HEALTH_THRESHOLD" ]; then CMD_ARRAY+=("--health-threshold" "$INPUT_HEALTH_THRESHOLD"); fi
if [ "${INPUT_ENFORCE_NAMESPACE:-false}" = "true" ]; then CMD_ARRAY+=("--enforce-namespace"); fi
if [ -n "$INPUT_FAIL_ON" ]; then CMD_ARRAY+=("--fail-on" "$INPUT_FAIL_ON"); fi
if [ "${INPUT_CHECK_DEPRECATIONS:-false}" = "true" ]; then CMD_ARRAY+=("--check-deprecations"); fi
if [ -n "$INPUT_OPA_BUNDLE" ]; then CMD_ARRAY+=("--opa-bundle" "$INPUT_OPA_BUNDLE"); fi
if [ -n "$INPUT_KYVERNO_REPORT" ]; then CMD_ARRAY+=("--kyverno-report" "$INPUT_KYVERNO_REPORT"); fi
if [ -n "$INPUT_OUTPUT" ]; then CMD_ARRAY+=("--output" "$INPUT_OUTPUT"); fi
if [ "$INPUT_STUB_REFS" != "" ]; then 
    if [ "$INPUT_STUB_REFS" = "*" ]; then CMD_ARRAY+=("--stub-refs"); else CMD_ARRAY+=("--stub-refs" "$INPUT_STUB_REFS"); fi
fi
if [ "$INPUT_UNSAFE" != "" ]; then 
    if [ "$INPUT_UNSAFE" = "*" ]; then CMD_ARRAY+=("--unsafe"); else CMD_ARRAY+=("--unsafe" "$INPUT_UNSAFE"); fi
fi
if [ -n "$INPUT_EVIDENCE_DIR" ]; then CMD_ARRAY+=("--evidence-dir" "$INPUT_EVIDENCE_DIR"); fi
if [ -n "$INPUT_ADAPTERS_DIR" ]; then CMD_ARRAY+=("--adapters-dir" "$INPUT_ADAPTERS_DIR"); fi

# [Security] Execute via exec or direct array call (no eval)
"${CMD_ARRAY[@]}"

# Check for changes
if [[ -n $(git status -s) ]]; then
  echo "✨ Healer found repairs! Committing changes..."
  git add .
  git commit -m "🩹 REPAIR: yamlr autonomous manifest correction"
  
  if [[ "$INPUT_PUSH" == "true" ]]; then
    echo "📤 Pushing repairs back to branch..."
    git push
  fi
else
  echo "✅ No repairs needed. Manifests are healthy."
fi
