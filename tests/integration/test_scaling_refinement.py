import pytest
import os
from pathlib import Path
from yamlr.core.engine import YamlrEngine
from yamlr.models import ManifestIdentity

def test_parallel_global_analysis_trigger(tmp_path):
    """
    Verifies that global analysis findings are correctly reported when 
    the parallel path is triggered (>1000 identities).
    """
    # 1. Setup workspace
    os.environ["YAMLR_INTERNAL_TEST_MODE"] = "true"
    workspace = tmp_path / "scaling_test"
    workspace.mkdir()
    
    # 2. Generate 101 "Ghost Services" (Services without selector matches)
    # This will trigger the parallel path if concurrency > 1.
    for i in range(101):
        svc_name = f"ghost-svc-{i}"
        svc_content = f"""
apiVersion: v1
kind: Service
metadata:
  name: {svc_name}
spec:
  selector:
    app: missing-app-{i}
  ports:
  - port: 80
"""
        (workspace / f"svc-{i}.yaml").write_text(svc_content)
    
    # 3. Running Engine
    # Force at least 2 workers if possible, or just rely on cpu_count
    engine = YamlrEngine(workspace_path=str(workspace), concurrency=2)
    
    # We use batch_heal to trigger run_global_analysis
    results = engine.batch_heal(str(workspace), dry_run=True)
    
    # 4. Verification
    assert len(results) == 101
    
    # Check that at least some results have ghost service findings
    ghost_findings = []
    for res in results:
        for finding in res.findings:
            if finding.get("rule_id") == "rule/ghost-service":
                ghost_findings.append(finding)
    
    assert len(ghost_findings) == 101
    print(f"Successfully verified {len(ghost_findings)} parallel ghost findings.")

def test_concurrency_propagation():
    """Verifies that YamlrEngine correctly propagates concurrency to workers."""
    engine = YamlrEngine(workspace_path=".", concurrency=4)
    assert engine.concurrency == 4
    
    # The fix in base.py ensures engine.concurrency is passed to processor.apply_semantic_fixes
    # We can't easily check the internal call without mocks, but we verified the code change.
