#!/bin/bash
set -e

# Assemble command into an array for safe execution (prevents shell injection)
CMD_ARRAY=("yamlr" "scan" "${INPUT_PATH:-.}")

# 1. Output format and destination
OUTPUT_TYPE="${INPUT_OUTPUT:-sarif}"
CMD_ARRAY+=("--output" "$OUTPUT_TYPE")

if [ -n "$INPUT_OUTPUT_FILE" ]; then
    CMD_ARRAY+=("--output-file" "$INPUT_OUTPUT_FILE")
fi

# 2. Kubernetes targeting
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

# 3. CI/CD gating
if [ -n "$INPUT_FAIL_ON" ]; then
    CMD_ARRAY+=("--fail-on" "$INPUT_FAIL_ON")
elif [ "${INPUT_FAIL_ON_ERROR:-true}" = "true" ] || [ "${INPUT_FAIL_ON_ERROR}" = "error" ]; then
    CMD_ARRAY+=("--fail-on" "error")
elif [ "${INPUT_FAIL_ON_ERROR}" = "warning" ]; then
    CMD_ARRAY+=("--fail-on" "warning")
elif [ "${INPUT_FAIL_ON_ERROR}" = "note" ] || [ "${INPUT_FAIL_ON_ERROR}" = "any" ]; then
    CMD_ARRAY+=("--fail-on" "note")
fi

if [ "${INPUT_EXIT_ZERO:-false}" = "true" ]; then
    CMD_ARRAY+=("--exit-zero")
fi

if [ "${INPUT_QUIET:-false}" = "true" ]; then
    CMD_ARRAY+=("--quiet")
fi

if [ "${INPUT_PUSH_TELEMETRY:-false}" = "true" ]; then
    CMD_ARRAY+=("--push-telemetry")
fi

# 4. Passthrough extra args
if [ -n "${INPUT_EXTRA_ARGS:-}" ]; then
    read -ra EXTRA_ARGS <<< "$INPUT_EXTRA_ARGS"
    CMD_ARRAY+=("${EXTRA_ARGS[@]}")
fi

echo "Yamlr Manifest Auditor starting..."
echo "Running: ${CMD_ARRAY[*]}"

# Execute via direct array call (no eval)
"${CMD_ARRAY[@]}"
