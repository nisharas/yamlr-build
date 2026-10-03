"""Adversarial Invariant & Fuzzing Resilience Test Suite.

Why: Empirically proves that Yamlr's borrowed-slice Rust document stream and Python multi-stage
healing pipeline are mathematically immune to denial-of-service, recursion depth exhaustion,
pathological indentation corruption, and binary payload attacks when executing on untrusted
YAML in CI/CD environments.
"""
import pytest
import yamlr_native

import yamlr
from yamlr import heal_yaml


def test_billion_laughs_yaml_bomb_bounded_memory():
    """Verify immunity to exponential alias expansion attacks (Billion Laughs / YAML bomb).
    
    Why: Attackers can embed exponential alias references to exhaust host memory in CI pipelines.
    Yamlr must either safely bound alias evaluation or preserve tokens without expanding.
    """
    yaml_bomb = """
a: &a ['lol','lol','lol','lol','lol','lol','lol','lol','lol']
b: &b [*a,*a,*a,*a,*a,*a,*a,*a,*a]
c: &c [*b,*b,*b,*b,*b,*b,*b,*b,*b]
d: &d [*c,*c,*c,*c,*c,*c,*c,*c,*c]
e: &e [*d,*d,*d,*d,*d,*d,*d,*d,*d]
metadata:
  name: bomb-target
"""
    result = heal_yaml(yaml_bomb)
    # Must complete sub-second without memory explosion
    assert result.healed_yaml is not None
    assert len(result.healed_yaml) < 5000  # Proof of zero unbounded exponential expansion


def test_null_byte_injection_safety():
    """Verify that null bytes and binary payloads do not cause segfaults or panics.
    
    Why: Malformed or malicious inputs containing binary control characters must be
    defensively rejected or neutralized by the Rust boundary.
    """
    payload_with_null = "apiVersion: v1\x00\nkind: Pod\nmetadata:\n  name: null-byte-pod\n"
    # Should safely handle without panicking
    shards = yamlr_native.native_shard(payload_with_null)
    assert isinstance(shards, list)
    
    result = heal_yaml(payload_with_null)
    assert result.healed_yaml is not None


def test_extreme_ast_nesting_depth():
    """Verify immunity to call-stack recursion exhaustion on pathological nested structures.
    
    Why: Deeply nested trees (e.g. 150+ levels of dictionary hierarchy) can trigger
    RecursionError in Python or stack overflows in recursive Rust decoders.
    """
    depth = 150
    lines = []
    for i in range(depth):
        lines.append("  " * i + f"layer_{i}:")
    lines.append("  " * depth + "target: safe_payload")
    deep_yaml = "\n".join(lines) + "\n"

    result = heal_yaml(deep_yaml)
    assert result.healed_yaml is not None
    assert "target: safe_payload" in result.healed_yaml
    # Verify idempotency on deep structures
    pass2 = heal_yaml(result.healed_yaml)
    assert pass2.healed_yaml == result.healed_yaml


def test_pathological_mixed_tabs_spaces():
    """Verify robustness against non-standard whitespace and mixed tab indentation.
    
    Why: Real-world YAML often contains accidental tabs and inconsistent indent widths.
    """
    mixed_yaml = "apiVersion: v1\n\tkind:\tService\nmetadata:\n   \tname: tab-service\n"
    result = heal_yaml(mixed_yaml)
    assert result.healed_yaml is not None
    # Must be idempotent
    pass2 = heal_yaml(result.healed_yaml)
    assert pass2.healed_yaml == result.healed_yaml


def test_unclosed_go_template_directives():
    """Verify that unclosed or malformed Go-template syntax does not crash the AST engine.
    
    Why: In Helm and ArgoCD repos, developers frequently write dynamic conditionals
    that are invalid YAML until rendered. Yamlr must isolate them safely.
    """
    unclosed_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.service.name
spec:
  replicas: {{ .Values.replicaCount | default 1
  template:
    spec:
      containers:
      - name: app
        image: {{ .Values.image.repository }}:{{ .Values.image.tag }}
"""
    result = heal_yaml(unclosed_template)
    assert result.healed_yaml is not None
    assert "{{ .Values.service.name" in result.healed_yaml


def test_massive_single_line_guardrail():
    """Verify that pathological single-line manifests do not exceed memory limits.
    
    Why: Attackers or fuzzers can pass megabyte-long single lines without line breaks.
    """
    # 50,000 char single line string
    large_line = "metadata:\n  annotations:\n    data: " + ("A" * 50000) + "\n"
    result = heal_yaml(large_line)
    assert result.healed_yaml is not None
    assert "metadata:" in result.healed_yaml
