#!/bin/bash
set -e

# Configure Git for the Surgeon
git config --global user.name "yamlr-surgeon[bot]"
git config --global user.email "surgeon@yamlr.dev"
git config --global --add safe.directory /github/workspace

echo "🔪 Yamlr Surgeon starting..."

# Default to current workspace if not provided
TARGET_PATH=${INPUT_PATH:-"."}

# Run the native Pro healer
CMD="yamlr heal \"$TARGET_PATH\" --confirm ${INPUT_EXTRA_ARGS:-}"

if [ "${INPUT_HARDEN:-false}" = "true" ]; then CMD="$CMD --harden"; fi
if [ "${INPUT_ENFORCE_LIMITS:-false}" = "true" ]; then CMD="$CMD --enforce-limits"; fi
if [ "${INPUT_ENFORCE_PROBES:-false}" = "true" ]; then CMD="$CMD --enforce-probes"; fi
if [ "${INPUT_FIX_REFS:-false}" = "true" ]; then CMD="$CMD --fix-refs"; fi
if [ "${INPUT_FIX_TAGS:-false}" = "true" ]; then CMD="$CMD --fix-tags"; fi
if [ -n "$INPUT_KUBE_VERSION" ]; then CMD="$CMD --kube-version $INPUT_KUBE_VERSION"; fi

eval $CMD

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
