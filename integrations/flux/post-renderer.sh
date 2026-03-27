#!/bin/bash
# Yamlr Flux Post-Renderer
# ------------------------
# This script acts as a Flux post-renderer for HelmRelease objects.
# It reads rendered YAML from stdin, heals it using Yamlr, and 
# outputs the pristine, valid YAML to stdout.
#
# Usage in HelmRelease:
# spec:
#   postRenderers:
#     - kustomize:
#         patches:
#           - patch: |
#               apiVersion: helm.toolkit.fluxcd.io/v2beta1
#               kind: HelmRelease
#               metadata:
#                 name: my-app
#               spec:
#                 postRenderers:
#                   - kustomize:
#                       images:
#                         - name: my-image
#                           newTag: v1.2.3
#
# Wait, Flux Post-Renderer is usually a binary/script.
# For Yamlr, we can use:
#
# spec:
#   postRenderers:
#     - kustomize: {} # Placeholder for native kustomize post-rendering
#
# Actually, the most robust way for Flux is to use the 'postRenderers' 
# with a script if using helm binary, but in GitOps controllers, 
# it's often handled via 'postRenderers' field in HelmRelease.
#
# Let's provide a generic script that can be used as a Flux post-renderer.

# 1. Capture stdin to a temporary file
TMP_FILE=$(mktemp)
cat > "$TMP_FILE"

# 2. Run Yamlr heal in clinical mode
# Note: Since it's stdin, we use '-' as the target.
# We force --yes-all and --output text for pure output.
yamlr heal "$TMP_FILE" --quiet --output text --yes-all

# 3. Cleanup
rm "$TMP_FILE"
