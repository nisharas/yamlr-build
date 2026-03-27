import pytest
import os
from yamlr.core.engine.base import YamlrEngine
from yamlr.models import HealConfig
from yamlr.core.pipeline import PipelinePlan, PipelineExecutor

def test_pipeline_plan_determinism():
    """Ensures that the same config always produces the same plan (Gate 🧊: Determinism)."""
    engine = YamlrEngine(workspace_path=".")
    config = HealConfig(dry_run=True, harden=True)
    
    plan1 = PipelinePlan.for_mode("heal", config, engine.pipeline)
    plan2 = PipelinePlan.for_mode("heal", config, engine.pipeline)
    
    assert [s.name for s in plan1.stages] == [s.name for s in plan2.stages]
    assert len(plan1.stages) > 5

def test_graph_integrity_relational_surgery(tmp_path):
    """Verifies that relational surgery correctly identifies ghost services in a mock workspace."""
    os.environ["YAMLR_INTERNAL_TEST_MODE"] = "true"
    workspace = tmp_path / "graph_test"
    workspace.mkdir()
    
    # Create a Service with no matching Pods
    svc_content = """
apiVersion: v1
kind: Service
metadata:
  name: orphan-svc
spec:
  selector:
    app: non-existent
  ports:
  - port: 80
"""
    (workspace / "svc.yaml").write_text(svc_content)
    
    engine = YamlrEngine(workspace_path=str(workspace), concurrency=1)
    
    # 1. First pass: audit_and_heal_file (includes relational surgery)
    # Note: In a workspace run, YamlrEngine.batch_heal handles the global analysis.
    results = engine.batch_heal(str(workspace), dry_run=True)
    
    assert len(results) == 1
    findings = results[0].findings
    
    # Should find the ghost service
    ghost_findings = [f for f in findings if f.get("rule_id") == "rule/ghost-service"]
    assert len(ghost_findings) == 1
    assert "orphan-svc" in ghost_findings[0].get("resource", "")

def test_executor_telemetry_aggregation(tmp_path):
    """Verifies that PipelineExecutor correctly aggregates stats into HealContext."""
    from yamlr.core.context import HealContext
    from yamlr.core.stages.base import PipelineStage
    from yamlr.models import PipelineStats
    
    class MockStage(PipelineStage):
        def run(self, context: HealContext) -> None:
            context.stats.lexer_typos += 5
            context.stats.semantic_repairs += 2

    engine = YamlrEngine(workspace_path=str(tmp_path))
    context = engine.pipeline.create_context("content: dummy", HealConfig())
    
    from yamlr.core.pipeline import StageSpec
    plan = PipelinePlan(mode="heal", stages=[StageSpec("Mock", MockStage, {})])
    
    executor = PipelineExecutor(plan)
    executor.execute(context)
    
    assert context.stats.lexer_typos == 5
    assert context.stats.semantic_repairs == 2

