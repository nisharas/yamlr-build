"""Unit tests for in-memory Helm Go-template token masker."""
import pytest

from yamlr.core.template_masker import mask_go_templates, unmask_go_templates


def test_mask_unmask_inline_values():
    raw = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.appName }}
spec:
  replicas: {{ .Values.replicaCount }}
  template:
    spec:
      containers:
      - name: web
        image: "{{ .Values.image.repo }}:{{ .Values.image.tag }}"
"""
    masked, token_map = mask_go_templates(raw)
    assert "__YAMLR_TMPL_VAL_" in masked
    assert "{{ .Values.appName }}" not in masked
    assert len(token_map) == 4

    restored = unmask_go_templates(masked, token_map)
    assert restored == raw


def test_mask_unmask_control_flow_lines():
    raw = """apiVersion: v1
kind: Service
metadata:
  name: my-svc
spec:
{{- if .Values.service.enabled }}
  type: ClusterIP
{{- end }}
"""
    masked, token_map = mask_go_templates(raw)
    assert "# __YAMLR_TMPL_LINE_" in masked
    assert "{{- if" not in masked

    restored = unmask_go_templates(masked, token_map)
    assert "{{- if .Values.service.enabled }}" in restored
    assert "{{- end }}" in restored
