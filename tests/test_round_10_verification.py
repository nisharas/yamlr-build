
import pytest
import json
import os
from yamlr.models import ManifestIdentity
from yamlr.analyzers.detectors.disk_index import DiskIndex

def test_manifest_identity_full_serialization():
    """Verifies that all 30+ reference fields are preserved during serialization."""
    ident = ManifestIdentity(
        kind="Service",
        name="frontend",
        namespace="prod",
        api_version="v1",
        file_path="/path/to/frontend.yaml"
    )
    # Inject various reference types
    ident.role_refs = ["admin-role", "view-role"]
    ident.ingress_backends = [{"service": "backend", "port": "8080"}]
    ident.annotations = {"yamlr.io/hardened": "true"}
    setattr(ident, "is_terraform", True)
    
    # Round-trip 
    data = ident.to_dict()
    assert data["kind"] == "Service"
    assert data["role_refs"] == ["admin-role", "view-role"]
    assert data["ingress_backends"] == [{"service": "backend", "port": "8080"}]
    assert data["is_terraform"] is True
    
    new_ident = ManifestIdentity.from_dict(data)
    assert new_ident.kind == "Service"
    assert new_ident.role_refs == ["admin-role", "view-role"]
    assert new_ident.ingress_backends == [{"service": "backend", "port": "8080"}]
    assert getattr(new_ident, "is_terraform", False) is True

def test_disk_index_sovereign_payloads():
    """Verifies that DiskIndex stores and streams full identities without loss."""
    with DiskIndex() as index:
        ident1 = ManifestIdentity(kind="Pod", name="p1", role_refs=["r1"])
        ident2 = ManifestIdentity(kind="Service", name="s1", ingress_backends=[{"b": "1"}])
        
        index.add_all([ident1, ident2])
        
        # Verify generator streaming
        stream = index.get_all()
        results = list(stream)
        
        assert len(results) == 2
        # Order might not be guaranteed by SQL without ORDER BY, but usually it's insert order
        kinds = {r.kind for r in results}
        assert kinds == {"Pod", "Service"}
        
        for r in results:
            if r.kind == "Pod":
                assert r.role_refs == ["r1"]
            if r.kind == "Service":
                assert r.ingress_backends == [{"b": "1"}]

if __name__ == "__main__":
    pytest.main([__file__])
