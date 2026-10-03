import pytest
import yamlr_native


def test_cncf_crd_schemas_loaded():
    """Verify that top-tier CNCF CRDs are embedded and returned by native schema loader."""
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    kinds = {s.kind for s in schemas}
    
    # Check top-tier CNCF CRD kinds
    expected_cncf_kinds = [
        "ServiceMonitor",
        "PrometheusRule",
        "Certificate",
        "Issuer",
        "ClusterIssuer",
        "VirtualService",
        "DestinationRule",
        "HTTPRoute",
        "Gateway",
        "Rollout",
        "Application",
    ]
    for kind in expected_cncf_kinds:
        assert kind in kinds, f"Expected CNCF CRD '{kind}' to be present in embedded schemas"

def test_cncf_crd_missing_spec_violation():
    """Verify that a CNCF CRD manifest missing required spec generates schema violation."""
    yaml_content = """apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: test-monitor
"""
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    violations = yamlr_native.native_check_schema_violations(yaml_content, schemas)
    assert any(v.field_path == "spec" for v in violations)

def test_cncf_crd_valid_manifest_passes():
    """Verify that a valid CNCF CRD manifest with spec passes schema validation."""
    yaml_content = """apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: example-tls
spec:
  secretName: example-tls-secret
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
"""
    schemas = yamlr_native.native_get_schema_for_version("1.30")
    violations = yamlr_native.native_check_schema_violations(yaml_content, schemas)
    # Certificate has required spec and metadata, so it should not have missing field violations
    assert not any(v.field_path in ("spec", "metadata", "apiVersion", "kind") for v in violations)
