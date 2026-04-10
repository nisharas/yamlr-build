import pytest
from unittest.mock import MagicMock, patch
from yamlr.pro.reconciliation.drift_doctor import DriftDoctor, ClusterStateRetriever

def test_drift_doctor_initialization():
    """Verify that DriftDoctor can be initialized with a retriever."""
    retriever = MagicMock(spec=ClusterStateRetriever)
    doctor = DriftDoctor(retriever=retriever)
    assert doctor.retriever == retriever

@patch("yamlr.pro.reconciliation.drift_doctor.ClusterStateRetriever")
def test_drift_doctor_recon_empty(mock_retriever_class):
    """Verify reconciliation with a missing resource."""
    mock_retriever = mock_retriever_class.return_value
    mock_retriever.get_live_resource.return_value = None
    
    doctor = DriftDoctor(retriever=mock_retriever)
    local = {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "test"}}
    results = doctor.reconcile(local, file_path="test.yaml")
    
    assert len(results) == 1
    assert "not found in cluster" in results[0].message

def test_semantic_cleaning_logic():
    """Verify that K8s system fields are cleaned during reconciliation."""
    doctor = DriftDoctor()
    raw_resource = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": "test-pod",
            "uid": "123-456",
            "resourceVersion": "999",
            "creationTimestamp": "2026-01-01T00:00:00Z",
            "managedFields": [{"manager": "kubelet"}]
        },
        "spec": {"containers": [{"image": "nginx"}]}
    }
    
    cleaned = doctor._clean_manifest(raw_resource)
    
    assert "uid" not in cleaned["metadata"]
    assert "resourceVersion" not in cleaned["metadata"]
    assert "creationTimestamp" not in cleaned["metadata"]
    assert "managedFields" not in cleaned["metadata"]
    assert cleaned["metadata"]["name"] == "test-pod"

def test_drift_detection():
    """Verify that semantic drift is detected when specs differ."""
    doctor = DriftDoctor()
    
    live = {
        "apiVersion": "v1",
        "kind": "Deployment",
        "metadata": {"name": "web"},
        "spec": {"replicas": 3}
    }
    
    local = {
        "apiVersion": "v1",
        "kind": "Deployment",
        "metadata": {"name": "web"},
        "spec": {"replicas": 1}
    }
    
    # Simulate reconciliation logic finding a match locally
    diff = doctor._generate_diff(local, live, "web")
    assert diff is not None
    assert "replicas" in str(diff)
