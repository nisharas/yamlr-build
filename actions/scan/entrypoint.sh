#!/bin/bash
set -e

CMD="yamlr scan \"${INPUT_PATH:-.}\" --output sarif ${INPUT_EXTRA_ARGS:-}"

if [ "${INPUT_FAIL_ON_ERROR:-true}" = "true" ] || [ "${INPUT_FAIL_ON_ERROR}" = "error" ]; then
    CMD="$CMD --fail-on error"
elif [ "${INPUT_FAIL_ON_ERROR}" = "warning" ]; then
    CMD="$CMD --fail-on warning"
elif [ "${INPUT_FAIL_ON_ERROR}" = "any" ]; then
    CMD="$CMD --fail-on any"
fi

if [ -n "$INPUT_KUBE_VERSION" ]; then
    CMD="$CMD --kube-version $INPUT_KUBE_VERSION"
fi

export GITHUB_TOKEN=$GITHUB_TOKEN

echo "Running: $CMD"
eval $CMD
