#!/bin/bash
set -e

# Assemble command into an array for safe execution (prevents shell injection)
# 1. Base command and path
CMD_ARRAY=("yamlr" "scan" "${INPUT_PATH:-.}")

# 2. Specific Inputs (Hardened defaults)
# Use 'sarif' as default output unless overridden
OUTPUT_TYPE="${INPUT_OUTPUT:-sarif}"
CMD_ARRAY+=("--output" "$OUTPUT_TYPE")

if [ -n "$INPUT_KUBE_VERSION" ]; then
    CMD_ARRAY+=("--kube-version" "$INPUT_KUBE_VERSION")
fi

if [ "${INPUT_FAIL_ON_ERROR:-true}" = "true" ] || [ "${INPUT_FAIL_ON_ERROR}" = "error" ]; then
    CMD_ARRAY+=("--fail-on" "error")
elif [ "${INPUT_FAIL_ON_ERROR}" = "warning" ]; then
    CMD_ARRAY+=("--fail-on" "warning")
elif [ "${INPUT_FAIL_ON_ERROR}" = "any" ]; then
    CMD_ARRAY+=("--fail-on" "any")
fi

# 3. Dynamic secondary flags
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
if [ "${INPUT_ENFORCE_LIMITS:-false}" = "true" ]; then CMD_ARRAY+=("--enforce-limits"); fi
if [ "${INPUT_ENFORCE_PROBES:-false}" = "true" ]; then CMD_ARRAY+=("--enforce-probes"); fi
if [ "${INPUT_ENFORCE_NAMESPACE:-false}" = "true" ]; then CMD_ARRAY+=("--enforce-namespace"); fi
if [ "${INPUT_FIX_TAGS:-false}" = "true" ]; then CMD_ARRAY+=("--fix-tags"); fi
if [ "${INPUT_HARDEN:-false}" = "true" ]; then CMD_ARRAY+=("--harden"); fi
if [ -n "$INPUT_FAIL_ON" ]; then CMD_ARRAY+=("--fail-on" "$INPUT_FAIL_ON"); fi
if [ "${INPUT_CHECK_DEPRECATIONS:-false}" = "true" ]; then CMD_ARRAY+=("--check-deprecations"); fi
if [ -n "$INPUT_OPA_BUNDLE" ]; then CMD_ARRAY+=("--opa-bundle" "$INPUT_OPA_BUNDLE"); fi
if [ -n "$INPUT_KYVERNO_REPORT" ]; then CMD_ARRAY+=("--kyverno-report" "$INPUT_KYVERNO_REPORT"); fi
if [ "${INPUT_FAST:-false}" = "true" ]; then CMD_ARRAY+=("--fast"); fi

# 4. Extra Args (Final override)
if [ -n "${INPUT_EXTRA_ARGS:-}" ]; then
    read -ra EXTRA_ARGS <<< "$INPUT_EXTRA_ARGS"
    CMD_ARRAY+=("${EXTRA_ARGS[@]}")
fi

export GITHUB_TOKEN=$GITHUB_TOKEN

echo "Running: ${CMD_ARRAY[*]}"

# [Security] Execute via exec or direct array call (no eval)
"${CMD_ARRAY[@]}"
