"""Tests for multiline Go-template masking and roundtrip restoration."""
import pytest

from yamlr.core.template_masker import mask_go_templates, unmask_go_templates


def test_multiline_go_template_directive():
    """Verify multiline if-statements and control blocks are masked and restored byte-for-byte."""
    raw_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
spec:
{{- if and
    .Values.autoscaling.enabled
    (gt (int .Values.autoscaling.minReplicas) 1) }}
  replicas: {{ .Values.autoscaling.minReplicas }}
{{- else }}
  replicas: {{ .Values.replicaCount }}
{{- end }}
"""
    masked, token_map = mask_go_templates(raw_template)
    assert "# __YAMLR_TMPL_LINE_" in masked
    assert "__YAMLR_TMPL_VAL_" in masked
    
    # Verify unmasking restores original content exactly
    restored = unmask_go_templates(masked, token_map)
    assert restored == raw_template


def test_indented_nested_template_blocks():
    """Verify indented multiline with blocks under mapping keys."""
    raw_template = """apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
    - name: app
      image: nginx:latest
{{- with .Values.resources }}
      resources:
        {{- toYaml . | nindent 8 }}
{{- end }}
"""
    masked, token_map = mask_go_templates(raw_template)
    restored = unmask_go_templates(masked, token_map)
    assert restored == raw_template
