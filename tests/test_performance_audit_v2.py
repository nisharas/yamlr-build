import unittest
import time
from pathlib import Path
from yamlr.core.engine.base import YamlrEngine
from yamlr.core.engine import auditor

class TestPerformanceAuditV2(unittest.TestCase):
    def setUp(self):
        self.workspace = Path(__file__).parent / "fixtures"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.workspace / "perf_test.yaml"
        self.manifest_content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: perf-app
spec:
  template:
    spec:
      containers:
      - name: app
        image: nginx:latest
        resources:
          requests:
            cpu: "100m"
      volumes:
      - name: cache
        hostPath:
          path: /tmp/unsafe
"""
        self.manifest_path.write_text(self.manifest_content)
        self.engine = YamlrEngine(workspace_path=str(self.workspace))

    def test_audit_performance_and_security_integration(self):
        """Verify that security penalties are applied without double-parsing."""
        # 1. Warm up
        auditor.audit_and_heal_file(self.engine, "perf_test.yaml", dry_run=True, harden=True)
        
        # 2. Measure
        start_t = time.time()
        res = auditor.audit_and_heal_file(self.engine, "perf_test.yaml", dry_run=True, harden=True)
        duration = time.time() - start_t
        
        print(f"\n[PERF] Audit duration: {duration:.3f}s")
        print(f"[DEBUG] Findings: {[ (f.get('rule_id') if isinstance(f, dict) else f.rule_id) for f in res.findings ]}")
        
        # 3. Verify Security Findings (Should still be present)
        # rule/no-latest-tag and rule/unsafe-hostpath
        rule_ids = [f["rule_id"] for f in res.findings]
        self.assertIn("rule/no-latest-tag", rule_ids)
        self.assertIn("rule/unsafe-hostpath", rule_ids)
        
        # 4. Verify Score Penalty
        # Base score starts high, but should be penalized by hostPath (-15) and latest tag
        self.assertLess(res.trust_score, 90)
        
        # 5. Verify no double-parse artifacts in logs (should only see Stage 7.5 once)
        security_logs = [log for log in res.logic_logs if "Stage 7.5: Security Scoring" in log]
        self.assertEqual(len(security_logs), 1)

if __name__ == "__main__":
    unittest.main()
