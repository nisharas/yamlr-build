"""
Yamlr PROCESSOR HELPERS
-----------------------
Helper functions for batch-level healing and global analysis.
Extracted from processor.py to maintain 100% modularity and line-count compliance.
"""

from __future__ import annotations
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Generator, Iterable

from yamlr.models import HealFileResult
from yamlr.core.entrypoints.base import get_console

logger = logging.getLogger("yamlr.engine.processor.helpers")

__all__ = [
    "prepare_batch_context",
    "check_batch_quota",
    "run_global_analysis",
    "record_batch_telemetry",
    "run_parallel_surgery_pool"
]

def prepare_batch_context(engine, config_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Constructs the standard engine context for batch processing.
    """
    return {
        "strict_validation": config_params.get("strict_validation", False),
        "compact": config_params.get("compact", False),
        "version": engine.cluster_version,
        "identity_mode": config_params.get("identity_mode", "infer"),
        "threshold": engine.health_threshold,
        "enforce_limits": config_params.get("enforce_limits", False) or engine.config.enforce_limits,
        "fix_tags": config_params.get("fix_tags", False) or engine.config.fix_tags,
        "harden": config_params.get("harden", False) or engine.config.harden,
        "enforce_probes": config_params.get("enforce_probes", False) or engine.config.enforce_probes,
        "dry_run": config_params.get("dry_run", True),
        "force_write": config_params.get("force_write", False),
        "skip_backup": config_params.get("skip_backup", False),
        "enforce_namespace": config_params.get("enforce_namespace", False) or engine.config.enforce_namespace,
        "fast": config_params.get("fast", False),
        "sovereign": config_params.get("sovereign", False),
        "check_deprecations": config_params.get("check_deprecations", False),
        "fix_refs": config_params.get("stub_healing") or config_params.get("allow_unsafe"),
        "pro_preview": config_params.get("pro_preview", False),
        "evidence_dir": config_params.get("evidence_dir"),
        "generate_receipts": config_params.get("generate_receipts", False),
        "adapters_dir": config_params.get("adapters_dir"),
        "from_report_path": config_params.get("from_report_path"),
        "allowed_host_paths": engine.allowed_host_paths,
        "quota_checked": True,
    }

def check_batch_quota(dry_run: bool, files_count: int):
    """
    Enforces the Free Tier healing quota for batch operations.
    """
    from yamlr.core.bridge import YamlrBridge
    capabilities = YamlrBridge.capabilities
    console = get_console()
    
    if not YamlrBridge.is_pro_enabled() and files_count >= 5:
        console.print(f"\n[bold yellow]⚠️  Community Quota Notice:[/bold yellow] This batch contains {files_count} files.")
        console.print("[dim]The Free tier is optimized for single-file focus. Batches > 5 files require [bold]Yamlr Pro[/bold] for deep graph analysis.[/dim]")
        
    if not dry_run and files_count > 0:
        is_allowed, _, msg = capabilities.can_heal(files_count)
        if not is_allowed:
            from yamlr.core.license_manager import LicenseManager
            LicenseManager.notify_quota_exceeded(msg)
            return False
    return True

def run_global_analysis(
    results: Optional[List[HealFileResult]], 
    tf_identities: List[Any], 
    file_map: Optional[Dict[str, HealFileResult]],
    index: Optional["DiskIndex"] = None,
    concurrency: int = 1
):
    """
    Performs global Cross-Resource Analysis across all discovered manifests.
    """
    all_identities = _collect_all_identities(results, tf_identities, index)
    if not all_identities:
        return

    try:
        from yamlr.core.resource_graph import ResourceGraph
        graph = ResourceGraph()
        # [ROUND-12] Support streaming build for ResourceGraph
        graph.build(all_identities)
        
        cross_findings = _execute_global_detectors(all_identities, graph, index, file_map, concurrency)
        if cross_findings:
            _attach_global_findings(cross_findings, file_map)
            
    except Exception as e:
        logger.warning(f"Global Graph Analysis failed: {e}")

def _execute_global_detectors(all_identities, graph, index, file_map, concurrency) -> List:
    """Selects and runs the appropriate analysis path based on scale."""
    from yamlr.analyzers.cross_resource import CrossResourceAnalyzer
    analyzer = CrossResourceAnalyzer()
    
    is_large = (index is not None or (isinstance(all_identities, list) and len(all_identities) > 100))
    if is_large and concurrency > 1:
        findings = []
        _run_large_global_analysis(all_identities, index, analyzer, file_map, concurrency, findings)
        return findings
    else:
        return analyzer.analyze(all_identities, graph=graph)

def _attach_global_findings(cross_findings: List, file_map: Dict):
    """Enriches and attaches cross-resource findings to individual results."""
    from yamlr.analyzers.risk_classifier import RiskClassifier
    norm_file_map = { str(Path(k).resolve()).lower(): v for k, v in file_map.items() }
    classifier = RiskClassifier()
    
    for finding in cross_findings:
        _enrich_and_attach_finding(finding, norm_file_map, classifier)

def _run_large_global_analysis(all_identities, index, analyzer, file_map, concurrency, cross_findings):
    """Execute parallel global analysis for large datasets with OOM protection."""
    logger.info("🚀 Global Analysis: Analyzing graph in parallel...")
    
    # [Zero-Blindspot] Avoid materializing 1M+ identities into RAM.
    # We use a streaming categorization pass to stay within constant RAM.
    services, workloads, configs, pvcs, pvs, cloud = _categorize_identities_streaming(all_identities)
    
    from yamlr.analyzers.detectors.base import build_index
    # build_index should also be made scale-aware or we use the disk index summary
    index_data = index.get_summary() if (index and hasattr(index, 'get_summary')) else build_index(workloads + services + configs)
    
    raw_findings = _execute_parallel_analysis_tasks(
        services, workloads, configs, pvcs, pvs, cloud, 
        index_data, analyzer.pro_mode, concurrency
    )
    
    norm_file_map = { str(Path(k).resolve()).lower(): v for k, v in file_map.items() }
    from yamlr.analyzers.risk_classifier import RiskClassifier
    classifier = RiskClassifier()
    
    for rf in raw_findings:
        temp_findings = []
        _map_finding_to_results(rf, analyzer, temp_findings)
        for f in temp_findings:
            cross_findings.append(f)
            _enrich_and_attach_finding(f, norm_file_map, classifier)

def _enrich_and_attach_finding(finding: Any, norm_file_map: Dict[str, HealFileResult], classifier: Any):
    """Enriches a single finding and attaches it to the corresponding result."""
    f_path = str(Path(finding.file_path).resolve()).lower()
    target_res = norm_file_map.get(f_path)
    if not target_res: return
    
    if target_res.logic_logs is None: target_res.logic_logs = []
    if target_res.findings is None: target_res.findings = []
    
    classifier.enrich_finding(finding)
    
    if not finding.impact_description:
         from yamlr.core.rule_manager import RuleManager
         rule_meta = RuleManager().get_rule(finding.rule_id)
         if rule_meta:
             finding.impact_description = rule_meta.get("impact_description")
             finding.rationale = finding.rationale or rule_meta.get("rationale")
    
    msg = f"Graph Analysis: {finding.message} ({finding.suggestion})"
    target_res.logic_logs.append(msg)

    target_res.findings.append({
        "stage": "Cross-Resource",
        "action_type": "detect",
        "target": f"{finding.resource_kind}/{finding.resource_name}",
        "description": finding.message,
        "message": finding.message,
        "severity": finding.severity.upper(),
        "suggestion": finding.suggestion,
        "rule_id": finding.rule_id,
        "rationale": finding.rationale,
        "impact_description": finding.impact_description,
        "risk_level": finding.risk_level
    })
    if finding.severity.upper() == "ERROR":
        target_res.success = False
        target_res.status = "FAILED"
    target_res.sem_status = "⚠️ FAIL"

def _categorize_identities_streaming(identities: Any) -> Tuple[List, List, List, List, List, List]:
    """
    Sorts identities into buckets using a single streaming pass.
    Why: Prevents loading the entire workspace manifest graph into memory.
    """
    services, workloads, configs, pvcs, pvs, cloud = [], [], [], [], [], []
    from yamlr.models import WORKLOAD_KINDS
    
    for i in identities:
        k = i.kind
        if k == "Service": services.append(i)
        elif k in WORKLOAD_KINDS: workloads.append(i)
        elif k in ("ConfigMap", "Secret"): configs.append(i)
        elif k == "PersistentVolumeClaim": pvcs.append(i)
        elif k == "PersistentVolume": pvs.append(i)
        if getattr(i, "is_terraform", False): cloud.append(i)
        
    return services, workloads, configs, pvcs, pvs, cloud

def _execute_parallel_analysis_tasks(services, workloads, configs, pvcs, pvs, cloud, index, pro_mode, concurrency) -> List[Dict]:
    """Orchestrates parallel detectors."""
    from yamlr.core.engine.worker import _execute_global_analysis_task
    from joblib import Parallel, delayed
    
    tasks = [
        {"type": "ghost_services", "services": [s.to_dict() for s in services], "workloads": [w.to_dict() for w in workloads], "pro_mode": pro_mode},
        {"type": "broken_refs", "identities": [w.to_dict() for w in workloads], "index": index, "pro_mode": pro_mode},
        {"type": "broken_volumes", "workloads": [w.to_dict() for w in workloads], "pvcs": [p.to_dict() for p in pvcs], "pro_mode": pro_mode},
        {"type": "port_mismatches", "services": [s.to_dict() for s in services], "workloads": [w.to_dict() for w in workloads], "pro_mode": pro_mode},
        {"type": "broken_cloud_refs", "pvs": [p.to_dict() for p in pvs], "cloud": [c.to_dict() for c in cloud], "pro_mode": pro_mode},
        {"type": "broken_credential_links", "secrets": [c.to_dict() for c in configs], "cloud": [c.to_dict() for c in cloud], "pro_mode": pro_mode}
    ]
    parallel_executor = Parallel(n_jobs=min(len(tasks), concurrency), prefer="processes")
    raw_results = parallel_executor(delayed(_execute_global_analysis_task)(t) for t in tasks)
    
    findings = []
    for r_list in raw_results:
        if r_list: findings.extend(r_list)
    return findings

def _map_finding_to_results(rf: Dict, analyzer: Any, cross_findings: List):
    """Dispatches raw findings to appropriate analyzer mapping logic."""
    if "service_name" in rf and "pod_name" in rf: # Port mismatch
        analyzer._map_ports([rf], cross_findings)
    elif "missing_pvc" in rf: # Broken volume
        analyzer._map_volumes([rf], cross_findings)
    elif "hint" in rf: # Ghost service 
        analyzer._map_ghosts([rf], cross_findings)
    elif "kind" in rf and "name" in rf and "resource_name" in rf: # Broken ref
        analyzer._map_broken_refs([rf], cross_findings)
    elif "volume_id" in rf: # Broken cloud ref
        analyzer._map_cloud_refs([rf], cross_findings)
    elif "is_credential_leak" in rf or ("name" in rf and "resource_kind" not in rf and "missing_pvc" not in rf): 
        analyzer._map_credential_links([rf], cross_findings)

def record_batch_telemetry(engine, results: List[HealFileResult], dry_run: bool, start_time: float):
    """
    Calculates summary metrics and records telemetry.
    """
    total_breakdown = {
        "lexer_repairs": 0, "lexer_typos": 0, "semantic_repairs": 0,
        "security_hardens": 0, "migrator_changes": 0
    }
    total_score = 0.0
    total_fixed = 0
    
    severity_rank = {"error": 100, "warning": 50, "info": 10, "none": 0}
    max_sev_label = "info"
    max_sev_rank = 0
    
    risk_rank = {"high": 100, "medium": 50, "low": 10, "none": 0}
    max_risk_label = "low"
    max_risk_rank = 0
    
    for res in results:
        total_score += getattr(res, "dna_integrity_score", 0) or 0
        s = getattr(res, "processing_stats", None) or {}
        for key in total_breakdown:
            total_breakdown[key] += s.get(key, 0)
        
        total_fixed += sum(s.get(k, 0) for k in total_breakdown.keys())
        
        for f in res.findings:
            sev = getattr(f, "severity", "info").lower()
            rank = severity_rank.get(sev, 10)
            if rank > max_sev_rank:
                max_sev_rank, max_sev_label = rank, sev
            
            risk = (getattr(f, "risk_level", "low") or "low").lower()
            rrank = risk_rank.get(risk, 10)
            if rrank > max_risk_rank:
                max_risk_rank, max_risk_label = rrank, risk

    avg_score = total_score / len(results) if results else 0.0
    duration = time.time() - start_time

    engine.telemetry.record_session(
        files_count=len(results),
        fixed_issues=total_fixed,
        avg_dna_score=avg_score,
        is_heal=not dry_run,
        max_severity=max_sev_label,
        max_risk=max_risk_label,
        breakdown=total_breakdown,
        duration_seconds=duration,
        bytes_processed=0
    )

def run_parallel_surgery_pool(engine, chunks, concurrency, stream_fh, is_ultra_scale, engine_context, progress, heal_task) -> Generator[HealFileResult, None, None]:
    """Orchestrates the parallel repair cycle."""
    from joblib import Parallel, delayed
    try:
         from joblib import exceptions
    except ImportError:
         exceptions = None
    from yamlr.core.engine.memmap import MemmapManager
    from yamlr.core.engine.worker import _execute_healing_chunk
    import json
    
    catalog_source = engine.catalog
    mem_manager = None
    if is_ultra_scale or len(json.dumps(engine.catalog)) > 1_000_000:
        mem_manager = MemmapManager(engine.config.runtime_dir)
        catalog_source = mem_manager.dump("catalog", engine.catalog)

    try:
        # [Round 13] Use signal-safe 'with' block to ensure process pool termination
        with Parallel(n_jobs=concurrency, prefer="processes", timeout=300) as parallel_executor:
            context = engine_context or {}
            iterable = (delayed(_execute_healing_chunk)({
                "files": c, "catalog_path": catalog_source if mem_manager else None,
                "catalog_data": engine.catalog if not mem_manager else None,
                "cpu_limit": engine.cpu_limit, "mem_limit": engine.mem_limit,
                "default_namespace": engine.default_namespace, "app_name": engine.app_name,
                "k8s_version": engine.cluster_version, "workspace_path": str(engine.workspace),
                "log_level": logging.getLogger("yamlr").getEffectiveLevel(),
                **context
            }) for c in chunks)
            
            try:
                try:
                    results_list = parallel_executor(iterable)
                except (TimeoutError, Exception) as e:
                    logger.error(f"❌ Critical Worker Failure: {e}")
                    results_list = []
                
                for chunk_results in results_list:
                    if chunk_results is None: continue
                    for res in _inflate_chunk_results(chunk_results):
                        if stream_fh:
                            stream_fh.write(json.dumps(res.to_dict()) + "\n")
                            stream_fh.flush()
                        
                        _prune_hyperscale_result(res, is_ultra_scale)
                        yield res
                        progress.update(heal_task, advance=1)
            except Exception as e:
                 logger.error(f"Hyperscale resolution error: {e}")
                 raise
    finally:
        if mem_manager:
            mem_manager.cleanup()

def _inflate_chunk_results(chunk_results: List) -> Generator[HealFileResult, None, None]:
    """Re-inflates worker results."""
    for res in chunk_results:
        if isinstance(res, dict) and res.get("_is_fast_dict"):
            from yamlr.models import HealAction
            yield HealFileResult(
                file_path=res["file_path"], full_path=res["full_path"],
                success=res["success"], status=res["status"],
                kind=res.get("kind", "Unknown"), logic_logs=res.get("logic_logs", []),
                findings=[HealAction(**f) for f in res["findings"]],
                dna_integrity_score=int(res["dna_integrity_score"]),
                identities=res.get("identities", [])
            )
        else:
            yield res

def _prune_hyperscale_result(res: HealFileResult, is_ultra_scale: bool):
    """Prunes results for memory efficiency."""
    if res.success:
        res.healed_content, res.raw_content = None, None
        if is_ultra_scale:
            res.logic_logs, res.findings = [], []

def _collect_all_identities(results: Optional[List], tf_identities: List, index: Optional["DiskIndex"]) -> Optional[Iterable]:
    """Unifies identities across sources."""
    if results:
        def gen_from_results():
            for res in results:
                path = res.full_path or res.file_path
                raw_ids = getattr(res, "identities_raw", []) or []
                for ident in raw_ids:
                    ident.file_path = path
                    yield ident
            if tf_identities:
                for tid in tf_identities: yield tid
        return gen_from_results()
    elif index:
        all_ids = index.get_all()
        if tf_identities:
            from itertools import chain
            return chain(all_ids, tf_identities)
        return all_ids
    elif tf_identities:
        return tf_identities
    return None
