
import pytest
from unittest.mock import MagicMock
from yamlr.core.engine.processor_helpers import _collect_all_identities, _categorize_identities_streaming
from yamlr.models import ManifestIdentity

def test_oom_safe_identity_streaming():
    """Verify that categorization works on generators without materialization."""
    def large_gen():
        for i in range(1000):
            yield ManifestIdentity(kind="Service", name=f"svc-{i}", namespace="default", api_version="v1")
            yield ManifestIdentity(kind="Deployment", name=f"dep-{i}", namespace="default", api_version="apps/v1")
    
    gen = large_gen()
    services, workloads, configs, pvcs, pvs, cloud = _categorize_identities_streaming(gen)
    
    assert len(services) == 1000
    assert len(workloads) == 1000
    # The key is that it didn't crash and processed the generator.

def test_collect_all_identities_returns_generator():
    """Verify that _collect_all_identities preserves generator status for OOM safety."""
    index = MagicMock()
    index.get_all.return_value = (i for i in range(5)) # mock generator
    
    res = _collect_all_identities(results=None, tf_identities=[], index=index)
    
    # It should not be a list
    assert not isinstance(res, list)
    # It should be iterable
    assert list(res) == [0, 1, 2, 3, 4]

if __name__ == "__main__":
    pytest.main([__file__])
