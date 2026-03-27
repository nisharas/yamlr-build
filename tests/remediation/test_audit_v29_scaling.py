import time
from yamlr.analyzers.detectors import CrossResourceDetectors
from yamlr.models import ManifestIdentity

def test_scaling_performance():
    """Quantifies the performance gain from pre-built indexing."""
    # Generate 5,000 resources (4,900 valid, 100 broken)
    identities = []
    
    # 4000 ConfigMaps
    for i in range(4000):
        identities.append(ManifestIdentity(kind="ConfigMap", name=f"cm-{i}", namespace="default"))
    
    # 1000 Deployments (900 valid, 100 broken)
    for i in range(1000):
        ref = f"cm-{i}" if i < 900 else f"cm-missing-{i}"
        identities.append(ManifestIdentity(kind="Deployment", name=f"app-{i}", namespace="default", config_refs=[ref]))

    print(f"\n🚀 Scaling Test: Analyzing {len(identities)} identities...")

    # Case 1: Detect without index (internal rebuild)
    start = time.time()
    broken1 = CrossResourceDetectors.detect_broken_refs(identities)
    dur1 = time.time() - start
    print(f"⏱️ Internal Index Build: {dur1:.4f}s (Found {len(broken1)})")

    # Case 2: Detect with pre-built index
    start_idx = time.time()
    index = CrossResourceDetectors.build_index(identities)
    dur_idx = time.time() - start_idx
    
    start = time.time()
    broken2 = CrossResourceDetectors.detect_broken_refs(identities, index=index)
    dur2 = time.time() - start
    print(f"⏱️ Pre-built Index Use: {dur2:.4f}s (Index Build: {dur_idx:.4f}s)")

    assert len(broken1) == 100
    assert len(broken2) == 100
    # In a real parallel scenario, dur2 would be the time per worker.
    
if __name__ == "__main__":
    test_scaling_performance()
