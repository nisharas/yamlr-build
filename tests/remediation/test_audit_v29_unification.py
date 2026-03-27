import pytest
from yamlr.analyzers.detectors import CrossResourceDetectors
from yamlr.analyzers.ref_resolver import ReferenceResolver
from yamlr.models import ManifestIdentity

def test_unification_parity():
    """Ensures both detectors.py and ref_resolver.py use the same logic."""
    identities = [
        ManifestIdentity(kind="Deployment", name="app", namespace="prod", config_refs=["cm-missing"]),
        ManifestIdentity(kind="ConfigMap", name="cm-exists", namespace="prod")
    ]
    
    # 1. Test Detector directly
    broken_detector = CrossResourceDetectors.detect_broken_refs(identities)
    assert len(broken_detector) == 1
    assert broken_detector[0]["name"] == "cm-missing"
    
    # 2. Test Resolver (Facade)
    resolver = ReferenceResolver()
    broken_resolver = resolver.resolve_references(identities)
    assert len(broken_resolver) == 1
    assert broken_resolver[0].message == "Broken reference: ConfigMap 'cm-missing' not found in namespace 'prod'."
    assert broken_resolver[0].fix_available is True
    assert broken_resolver[0].fix_id == "ConfigMap:cm-missing:prod"

def test_index_sharing():
    """Ensures the pre-built index is correctly utilized."""
    identities = [
        ManifestIdentity(kind="Deployment", name="app", namespace="default", config_refs=["secret-missing"]),
        ManifestIdentity(kind="Secret", name="secret-exists", namespace="default")
    ]
    
    # Pre-build index
    index = CrossResourceDetectors.build_index(identities)
    assert "Secret" in index
    assert "secret-exists" in index["Secret"]["default"]
    
    # Validate using pre-built index
    broken = CrossResourceDetectors.detect_broken_refs(identities, index=index)
    assert len(broken) == 1
    assert broken[0]["name"] == "secret-missing"

def test_healer_robustness():
    """Ensures MissingTargetHealer handles both dicts and AnalysisResult objects."""
    from yamlr.healers.semantic.missing_target import MissingTargetHealer
    from yamlr.analyzers.base import AnalysisResult
    
    healer = MissingTargetHealer()
    cli_flags = {"stub_refs": True}
    
    # Case 1: Raw Dict
    dict_issue = {
        "kind": "ConfigMap", "name": "cm1", "namespace": "ns1", "rule_id": "missing-configmap-ref"
    }
    stubs_d, _ = healer.heal([dict_issue], cli_flags)
    assert len(stubs_d) == 1
    assert stubs_d[0]["metadata"]["name"] == "cm1"
    
    # Case 2: AnalysisResult Object
    obj_issue = AnalysisResult(
        analyzer_name="test", severity="ERROR", message="msg",
        resource_name="src", resource_kind="Deployment", file_path="path",
        rule_id="missing-configmap-ref", fix_available=True, fix_id="ConfigMap:cm2:ns2"
    )
    stubs_o, _ = healer.heal([obj_issue], cli_flags)
    assert len(stubs_o) == 1
    assert stubs_o[0]["metadata"]["name"] == "cm2"
    assert stubs_o[0]["metadata"]["namespace"] == "ns2"

if __name__ == "__main__":
    pytest.main([__file__])
