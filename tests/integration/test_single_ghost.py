import os
import pytest
from pathlib import Path
from yamlr.core.engine import YamlrEngine

def test_single_ghost_service(tmp_path):
    """Deep trace of a single ghost service identification."""
    os.environ["YAMLR_INTERNAL_TEST_MODE"] = "true"
    workspace = tmp_path / "single_test"
    workspace.mkdir()
    
    svc_content = """
apiVersion: v1
kind: Service
metadata:
  name: ghost-svc
spec:
  selector:
    app: missing-app
  ports:
  - port: 80
"""
    (workspace / "svc.yaml").write_text(svc_content)
    
    engine = YamlrEngine(workspace_path=str(workspace), concurrency=1)
    results = engine.batch_heal(str(workspace), dry_run=True)
    
    print(f"\nDEBUG: Results count: {len(results)}")
    if results:
        res = results[0]
        print(f"DEBUG: Status: {res.status}")
        print(f"DEBUG: Identities count: {len(res.identities)}")
        if hasattr(res, "identities_raw"):
            print(f"DEBUG: Raw Identities count: {len(res.identities_raw)}")
            if res.identities_raw:
                print(f"DEBUG: Raw Identities Selector: {res.identities_raw[0].selector}")
        print(f"DEBUG: Findings: {res.findings}")
        print(f"DEBUG: Audit Log Tail: {res.logic_logs[-5:] if res.logic_logs else []}")
        
    assert len(results) == 1
    assert any(f.get("rule_id") == "rule/ghost-service" for f in results[0].findings)
