from __future__ import annotations
import logging
from typing import Any, Dict, List

logger = logging.getLogger("yamlr.engine.stages.analyze")

def execute_analyze_stage(engine: Any, content: str, relative_path: str, _ingest_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Macro-Stage 2: Analyze (Schema/Semantic).
    
    Why: Multi-dimensional violation detection for Kubernetes manifests.
    """
    findings = []
    findings.extend(run_schema_validation(engine, content, relative_path))
    findings.extend(run_semantic_analyzers(engine, content, relative_path))
    return {"findings": findings}

def run_schema_validation(engine: Any, content: str, relative_path: str) -> List[Any]:
    """Executes Stage 2.1: Schema Validation."""
    from yamlr.core.engine.models import AnalysisResult
    results = []
    try:
        from yamlr.parsers.structurer import SchemaValidator
        validator = SchemaValidator(catalog=engine.catalog, cluster_version=engine.cluster_version)
        schema_findings = validator.validate(content, relative_path)
        for f in schema_findings:
            results.append(
                AnalysisResult(
                    analyzer_name="SchemaValidator",
                    severity=f.get("severity", "ERROR"),
                    message=f.get("message", "Schema violation"),
                    resource_name=f.get("resource_name", "unknown"),
                    resource_kind=f.get("resource_kind", "unknown"),
                    file_path=relative_path,
                    rule_id=f.get("rule_id", "SCHEMA-01"),
                    line_no=f.get("line_no"),
                    column_no=f.get("column_no"),
                )
            )
    except Exception as e:
        logger.debug(f"Schema validation failed for {relative_path}: {e}")
    return results

def run_semantic_analyzers(engine: Any, content: str, relative_path: str) -> List[Any]:
    """Executes Stage 2.2: Semantic Analysis."""
    from yamlr.analyzers.registry import AnalyzerRegistry
    import yaml
    
    results = []
    analyzers = AnalyzerRegistry.get_all_analyzers(catalog=engine.catalog)
    
    try:
        resources = [r for r in yaml.safe_load_all(content) if isinstance(r, dict)]
    except Exception:
        resources = []
        
    for analyzer in analyzers:
        execute_single_analyzer(analyzer, content, relative_path, resources, results)
        
    return results

def execute_single_analyzer(analyzer: Any, content: str, relative_path: str, resources: List[Dict[str, Any]], results: List[Any]):
    """Helper to isolate single analyzer execution logic."""
    from yamlr.core.engine.models import AnalysisResult
    try:
        if getattr(analyzer, "analyzer_type", "metadata") == "batch":
            return
            
        analyzer_findings = analyzer.analyze(
            resources if not getattr(analyzer, "raw_mode", False) else content,
            file_path=relative_path,
            content=content,
        )
        
        if not isinstance(analyzer_findings, list):
            return
            
        for f in analyzer_findings:
            if isinstance(f, dict):
                results.append(
                    AnalysisResult(
                        analyzer_name=analyzer.__class__.__name__,
                        severity=f.get("severity", "WARNING"),
                        message=f.get("message", "Semantic finding"),
                        resource_name=f.get("resource_name", "unknown"),
                        resource_kind=f.get("resource_kind", "unknown"),
                        file_path=relative_path,
                        rule_id=f.get("rule_id", "SEM-01"),
                        line_no=f.get("line_no"),
                        column_no=f.get("column_no"),
                    )
                )
            elif hasattr(f, "severity"):  # AnalysisResult object
                results.append(f)
    except Exception as e:
        logger.error(f"Analyzer {analyzer.__class__.__name__} failed: {e}")
