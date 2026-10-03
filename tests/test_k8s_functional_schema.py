"""Functional Schema Validation & Semantic Correctness Test Suite.

Why: Empirically proves that Yamlr's healing mutations produce semantically valid
Kubernetes resources adhering to the official OpenAPI v3 schema (simulating admission
validation in an API server), closing the gap between textual invariance and operational
deployability.
"""
import sys
from pathlib import Path

import pytest

# Ensure scripts directory can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yamlr_native

import yamlr
from scripts.run_golden_corpus import UPSTREAM_MANIFESTS, split_yaml_documents
from yamlr import heal_yaml


@pytest.fixture(scope="module")
def k8s_schemas():
    """Load native Kubernetes OpenAPI schemas for v1.30."""
    return yamlr_native.native_get_schema_for_version("1.30")


def test_workload_missing_spec_detected(k8s_schemas):
    """Verify that incomplete workloads missing required 'spec' are correctly caught."""
    incomplete_deploy = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: broken-deploy
"""
    violations = yamlr_native.native_check_schema_violations(incomplete_deploy, k8s_schemas)
    spec_violations = [v for v in violations if v.field_path == "spec"]
    assert len(spec_violations) == 1
    assert "Missing required field 'spec'" in spec_violations[0].message


def test_non_workload_without_spec_is_valid(k8s_schemas):
    """Verify that non-workloads (Namespace, ConfigMap, Secret) are not falsely flagged for missing spec."""
    valid_namespace = """apiVersion: v1
kind: Namespace
metadata:
  name: production-env
"""
    violations = yamlr_native.native_check_schema_violations(valid_namespace, k8s_schemas)
    assert len(violations) == 0

    valid_configmap = """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  key: value
"""
    violations_cm = yamlr_native.native_check_schema_violations(valid_configmap, k8s_schemas)
    assert len(violations_cm) == 0


def test_golden_corpus_post_heal_functional_schema_validity(k8s_schemas):
    """Verify that 100% of healed Golden Corpus manifests adhere to Kubernetes schemas."""
    cache_dir = Path("corpus/golden_corpus")
    total_docs_checked = 0

    for name, meta in UPSTREAM_MANIFESTS.items():
        manifest_file = cache_dir / meta["file"]
        if not manifest_file.exists():
            continue

        raw_yaml = manifest_file.read_text(encoding="utf-8", errors="ignore")
        docs = split_yaml_documents(raw_yaml)

        for doc in docs:
            # Heal manifest
            healed_result = heal_yaml(doc)
            healed_yaml = healed_result.healed_yaml

            # Validate against Kubernetes OpenAPI schema
            violations = yamlr_native.native_check_schema_violations(healed_yaml, k8s_schemas)
            assert len(violations) == 0, f"Schema violation detected in {name}: {[v.message for v in violations]}"
            total_docs_checked += 1

    assert total_docs_checked >= 95, f"Expected at least 95 documents evaluated, got {total_docs_checked}"
