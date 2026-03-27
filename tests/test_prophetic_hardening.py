import pytest
from yamlr.parsers.lexer import YamlrLexer
from yamlr.core.pipeline import HealingPipeline
from yamlr.models import HealConfig

def test_boolean_guard_heuristic():
    lexer = YamlrLexer()
    # YAML 1.1 booleans that should be quoted
    raw_yaml = """
key1: yes
key2: no
key3: on
key4: off
"""
    shards = lexer.shard(raw_yaml)
    
    # Check if they are quoted in shards
    expected_values = {
        "key1": '"yes"',
        "key2": '"no"',
        "key3": '"on"',
        "key4": '"off"'
    }
    for shard in shards:
        if shard.key in expected_values:
            assert shard.value == expected_values[shard.key]

def test_flow_style_sanitizer():
    lexer = YamlrLexer()
    raw_yaml = """
list: [a, b, ]
dict: {k1: v1, k2: v2, }
"""
    shards = lexer.shard(raw_yaml)
    
    # Check if trailing commas are gone in raw_line
    for shard in shards:
        if shard.key == "list":
            assert shard.value == "[a, b]"
        if shard.key == "dict":
            assert shard.value == "{k1: v1, k2: v2}"

def test_namespace_enforcement_analyzer():
    # Use real pipeline to check analyzer + healer
    catalog = {} # Minimal catalog
    pipeline = HealingPipeline(catalog=catalog, default_namespace="prod-namespace")
    
    raw_yaml = """
apiVersion: v1
kind: Service
metadata:
  name: my-svc
spec:
  ports:
  - port: 80
"""
    config = HealConfig(enforce_namespace=True)
    result = pipeline.heal(raw_yaml, config=config)
    
    # 1. Check if finding was generated
    findings = [f for f in result.findings if f.rule_id == "rule/missing-namespace"]
    assert len(findings) > 0
    
    # 2. Check if healed correctly
    assert "namespace: prod-namespace" in result.content

def test_namespace_enforcement_skipped_for_cluster_scoped():
    catalog = {}
    pipeline = HealingPipeline(catalog=catalog, default_namespace="prod-namespace")
    
    raw_yaml = """
apiVersion: v1
kind: Namespace
metadata:
  name: some-ns
"""
    config = HealConfig(enforce_namespace=True)
    result = pipeline.heal(raw_yaml, config=config)
    
    # 1. Should NOT have a finding
    findings = [f for f in result.findings if f.rule_id == "rule/missing-namespace"]
    assert len(findings) == 0
    
    # 2. Should NOT have injected namespace
    assert "namespace: prod-namespace" not in result.content
