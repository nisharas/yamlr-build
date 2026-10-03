import pytest

from yamlr.core.template_masker import mask_go_templates, unmask_go_templates


def test_dynamic_key_expression_masking():
    template = """apiVersion: v1
kind: ConfigMap
metadata:
  name: dynamic-keys-config
data:
  {{ .Values.dynamicKeyName }}: "dynamic-value"
  {{ printf "prefix-%s" .Values.env }}: "computed-value"
  regularKey: {{ .Values.regularValue }}
"""
    masked, token_map = mask_go_templates(template)
    assert "__YAMLR_TMPL_KEY_0__: \"dynamic-value\"" in masked
    assert "__YAMLR_TMPL_KEY_1__: \"computed-value\"" in masked
    assert "regularKey: __YAMLR_TMPL_VAL_2__" in masked

    unmasked = unmask_go_templates(masked, token_map)
    assert unmasked == template


def test_dynamic_key_with_sharding_roundtrip():
    import yamlr_native

    template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  labels:
    app: nginx
    {{ .Values.environmentKey }}: production
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.25.0
"""
    masked, token_map = mask_go_templates(template)
    shards = yamlr_native.native_shard(masked)
    assert len(shards) > 0

    reconstructed = yamlr_native.native_reconstruct_yaml(shards)
    final_yaml = unmask_go_templates(reconstructed, token_map)

    assert "{{ .Values.environmentKey }}: production" in final_yaml
    assert "image: nginx:1.25.0" in final_yaml
